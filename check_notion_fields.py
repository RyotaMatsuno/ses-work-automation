import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import dotenv_values
config = dotenv_values('config/.env')
headers = {
    'Authorization': f'Bearer {config["NOTION_API_KEY"]}',
    'Notion-Version': '2022-06-28'
}

r1 = requests.get('https://api.notion.com/v1/databases/343450ff-37c0-819d-8769-fb0a8a4ceeb1', headers=headers)
props1 = r1.json().get('properties', {})
print('=== エンジニアDB ===', flush=True)
for k, v in props1.items():
    print(f'  {k} ({v["type"]})', flush=True)

r2 = requests.get('https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c', headers=headers)
props2 = r2.json().get('properties', {})
print('=== 案件DB ===', flush=True)
for k, v in props2.items():
    print(f'  {k} ({v["type"]})', flush=True)
