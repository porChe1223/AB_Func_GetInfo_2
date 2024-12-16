# 手順

## ローカルデバック

- lsof -i
- kill -9 <localhost:9091 の PID>
- python3 -m venv .venv
- . .venv/bin/activate
- pip install -r requirements.txt
- F5

## デプロイ

- https://ga4info.azurewebsites.net/main

# 注意

- Python 3.11.11
