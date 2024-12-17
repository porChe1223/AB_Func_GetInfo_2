import azure.functions as func
import logging
import json
import os
from dotenv import load_dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric, OrderBy

# .envファイルをロード
load_dotenv()
# Google Cloudの認証情報
credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if credentials_path:
    print(f"Google Cloud Credentials Path: {credentials_path}")
else:
    print("環境変数 'GOOGLE_APPLICATION_CREDENTIALS' が設定されていません。")

# サービスアカウントJSONファイルのパス
KEY_FILE_LOCATION = "ga4account.json"

# GA4のプロパティID
PROPERTY_ID = "469101596"

###########################
# GA4からのレポート情報取得 #
###########################
def get_ga4_report():
    # クライアントの初期化
    client = BetaAnalyticsDataClient.from_service_account_file(KEY_FILE_LOCATION)

    # レポートリクエストの設定
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="2023-01-01", end_date="today")],
        dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
        metrics=[Metric(name="screenPageViews")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=10,
    )

    # レポートの取得
    return client.run_report(request)


############################
# レポートをJSON辞書型に変換 #
############################
def format_response_as_json(response):
    result = []
    for row in response.rows:
        data = {
            "dimensions": {dim_name: dim_value.value for dim_name, dim_value in zip(["pagePath", "pageTitle"], row.dimension_values)},
            "metrics": {metric_name: metric_value.value for metric_name, metric_value in zip(["screenPageViews"], row.metric_values)}
        }
        result.append(data)
    return json.dumps(result, indent=4, ensure_ascii=False)

#################################
# レポート情報をデータベースに格納 #
#################################
# エンドポイント
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="get", auth_level=func.AuthLevel.ANONYMOUS)
@app.queue_output(arg_name="msg", queue_name="outqueue", connection="AzureWebJobsStorage")
@app.cosmos_db_output(arg_name="outputDocument",
                      connection="CosmosDbConnectionSetting",
                      database_name="GA4info",
                      container_name="container-1")
def main(req: func.HttpRequest,
         msg: func.Out[func.QueueMessage],
         outputDocument: func.Out[func.Document])-> func.HttpResponse:
    cosmos_db_connection_string = os.getenv('CosmosDbConnectionSetting')
    azure_storage_connection_string = os.getenv('AzureWebJobsStorage')

    logging.info(f"CosmosDB Connection String: {cosmos_db_connection_string}")
    logging.info(f"Azure Storage: {azure_storage_connection_string}")
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        # GA4からのレポート情報取得
        response = get_ga4_report()
        # レポート情報をJSON型に変換
        result = format_response_as_json(response)

        # # Cosmos DB に出力
        # for result in results:
        #     outputDocument.set(func.Document.from_json(json.dumps(result)))

        # デバッグ用ログ
        logging.info(f"Results: {result}")

        # JSONレスポンスを返す
        return func.HttpResponse(result, status_code=200)
    except Exception as e:
        logging.error(f'エラーが発生しました: {e}')
        return func.HttpResponse(f'エラーが発生しました: {e}', status_code=500)