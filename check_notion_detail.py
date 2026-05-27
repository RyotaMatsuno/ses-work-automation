# -*- coding: utf-8 -*-
import sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from dotenv import dotenv_values

env = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
NOTION_KEY = env.get('NOTION_API_KEY') or env.get('NOTION_TOKEN')
PROJECT_DB = '343450ff-37c0-81e4-934e-f25f90284a3c'

headers = {'Authorization': f'Bearer {NOTION_KEY}', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json'}

# 今日の案件1件取得して案件詳細フィールドの中身を確認
import datetime
today = datetime.datetime.now().strftime('%Y-%m-%d') + 'T00:00:00'
r = requests.post(f'https://api.notion.com/v1/databases/{PROJECT_DB}/query', headers=headers, json={
    'filter': {'timestamp': 'created_time', 'created_time': {'on_or_after': today}},
    'sorts': [{'timestamp': 'created_time', 'direction': 'descending'}],
    'page_size': 1
})
results = r.json().get('results', [])
if results:
    p = results[0]
    props = p.get('properties', {})
    title = ''.join([t.get('plain_text','') for t in props.get('案件名', {}).get('title', [])])
    print(f'案件名: {title}')
    detail_items = props.get('案件詳細', {}).get('rich_text', [])
    detail = ''.join([t.get('plain_text','') for t in detail_items])
    print(f'案件詳細 ({len(detail)}文字):')
    print(detail[:500])
