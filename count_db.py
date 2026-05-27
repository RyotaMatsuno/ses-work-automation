
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
import requests

config = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
headers = {
    'Authorization': f'Bearer {config["NOTION_API_KEY"]}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

def count_db(db_id, label):
    results = []
    payload = {'page_size': 100}
    while True:
        r = requests.post(f'https://api.notion.com/v1/databases/{db_id}/query', headers=headers, json=payload)
        data = r.json()
        results.extend(data.get('results', []))
        if not data.get('has_more'):
            break
        payload['start_cursor'] = data['next_cursor']
    print(f'{label}: 合計{len(results)}件')
    # ステータス別集計
    statuses = {}
    for p in results:
        props = p['properties']
        # 案件DBはステータス、エンジニアDBは稼働状況
        s = (props.get('ステータス') or props.get('稼働状況') or {}).get('select', {})
        name = s.get('name', '未設定') if s else '未設定'
        statuses[name] = statuses.get(name, 0) + 1
    for k, v in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f'  {k}: {v}件')

count_db('343450ff-37c0-81e4-934e-f25f90284a3c', '案件DB')
print()
count_db('343450ff-37c0-819d-8769-fb0a8a4ceeb1', 'エンジニアDB')
