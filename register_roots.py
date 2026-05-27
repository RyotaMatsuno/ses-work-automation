
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
import requests, json

config = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
NOTION_KEY = config['NOTION_API_KEY']
PROJECT_DB = config.get('NOTION_PROJECT_DB_ID', '343450ff-37c0-81e4-934e-f25f90284a3c')
headers = {
    'Authorization': f'Bearer {NOTION_KEY}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

RAW_BODY = """■案件名 基幹システム移行支援

■期間 6月～

■勤務形態 リモート併用（八丁堀） ※週3日出社

■必須スキル ・要件定義経験5年以上

■尚可スキル ・java,springベースでの経験 ・Postgreの経験 ・フロントに立って顧客と直接の折衝経験 ・住宅系の知見 ・基幹システムの移行経験

■商流制限 貴社社員・貴社所属の個人事業主まで ※営業支援費対応が可能でしたら、貴社１社先まで

■年齢制限 50代前半まで

■外国籍 不可

■稼働率 100%

■単価 ～75万円 ※スキル見合い

■精算条件 精算有り　140-180h　上下割

■支払サイト 月末締め翌々月5日払い（35日）

■募集人数 1名

■面談回数 2回（Web）

■業務内容 住宅系のお客様基幹システムの移行にあたり、業務チームで要件定義を実施していただきます。システムはjava,springベース。DBはPostgre。対応範囲は要件定義～詳細設計を想定しております。

■備考 ・短期（6カ月以内）が多い方はNGです ・長期で参画可能な方のみ ・服装：オフィスカジュアル

■お願い ご提案いただく際に、必須・尚可のマッチ度（可能でしたらスキルコメントも）をお教えください。"""

SUMMARY = """【案件要約】
案件名: 基幹システム移行支援（Roots）
単価: ～75万円（スキル見合い）
期間: 6月〜（長期）
勤務: リモート併用・八丁堀、週3出社
面談: 2回（Web）
外国籍: 不可
必須: 要件定義経験5年以上
尚可: Java/Spring、PostgreSQL、顧客折衝、住宅系知見、基幹移行経験
備考: 短期NGあり、50代前半まで、商流1社まで"""

NOTE_CONTENT = SUMMARY + "\n\n【原文】\n" + RAW_BODY

def split_rich_text(text, chunk=1900):
    return [{'text': {'content': text[i:i+chunk]}} for i in range(0, len(text), chunk)] or [{'text': {'content': ''}}]

properties = {
    '案件名': {'title': [{'text': {'content': '基幹システム移行支援（Roots）'}}]},
    'ステータス': {'select': {'name': '募集中'}},
    '案件詳細': {'rich_text': split_rich_text(NOTE_CONTENT)},
    '必要スキル': {'multi_select': [{'name': '要件定義'}]},
    '尚可スキル': {'multi_select': [
        {'name': 'Java'}, {'name': 'Spring'}, {'name': 'PostgreSQL'}
    ]},
    '単価（万円）': {'number': 75},
    '開始日': {'date': {'start': '2025-06-01'}},
    '勤務地': {'rich_text': [{'text': {'content': '八丁堀（リモート併用・週3出社）'}}]},
    '所属会社名': {'rich_text': [{'text': {'content': 'ルーツ・テクノロジーズ'}}]},
    '入力元': {'select': {'name': '共通メール'}},
}

res = requests.post('https://api.notion.com/v1/pages',
    headers=headers,
    json={'parent': {'database_id': PROJECT_DB}, 'properties': properties})

if res.status_code == 200:
    page_id = res.json()['id']
    page_url = res.json().get('url', '')
    print(f'OK: Notion登録完了')
    print(f'URL: {page_url}')
    print(f'ID: {page_id}')
else:
    print(f'NG: {res.status_code} {res.text[:300]}')
    page_url = ''
    page_id = ''
