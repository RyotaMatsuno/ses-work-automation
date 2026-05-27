# -*- coding: utf-8 -*-
import sys, io, requests, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from dotenv import dotenv_values

env = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
NOTION_KEY = env.get('NOTION_API_KEY') or env.get('NOTION_TOKEN')
PROJECT_DB = '343450ff-37c0-81e4-934e-f25f90284a3c'
ENGINEER_DB = '343450ff-37c0-819d-8769-fb0a8a4ceeb1'

headers = {
    'Authorization': f'Bearer {NOTION_KEY}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

cutoff = (datetime.datetime.now() - datetime.timedelta(hours=2)).isoformat()

# 直近2時間の案件登録
r = requests.post(f'https://api.notion.com/v1/databases/{PROJECT_DB}/query', headers=headers, json={
    'filter': {'timestamp': 'created_time', 'created_time': {'on_or_after': cutoff}},
    'sorts': [{'timestamp': 'created_time', 'direction': 'descending'}],
    'page_size': 50
})
projects = r.json().get('results', [])
print(f'=== 直近2時間の新規案件: {len(projects)}件 ===')
for p in projects:
    props = p.get('properties', {})
    title = ''.join([t.get('plain_text','') for t in props.get('案件名', {}).get('title', [])])
    print(f'  {p["created_time"][:16]} | {title[:40]}')

# 直近2時間の人材登録
r2 = requests.post(f'https://api.notion.com/v1/databases/{ENGINEER_DB}/query', headers=headers, json={
    'filter': {'timestamp': 'created_time', 'created_time': {'on_or_after': cutoff}},
    'sorts': [{'timestamp': 'created_time', 'direction': 'descending'}],
    'page_size': 50
})
engineers = r2.json().get('results', [])
print(f'\n=== 直近2時間の新規人材: {len(engineers)}件 ===')
for e in engineers:
    props = e.get('properties', {})
    title = ''.join([t.get('plain_text','') for t in props.get('名前', {}).get('title', [])])
    print(f'  {e["created_time"][:16]} | {title[:30]}')
