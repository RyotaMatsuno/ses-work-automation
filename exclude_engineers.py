
# -*- coding: utf-8 -*-
import requests, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
ENGINEER_DB = '343450ff-37c0-819d-8769-fb0a8a4ceeb1'

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def query_db(db_id):
    results, payload = [], {"page_size": 100}
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                         headers=headers, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"): break
        payload["start_cursor"] = data["next_cursor"]
    return results

eng_all = query_db(ENGINEER_DB)

# 除外対象の定義
# - コンサル/PMO系人材（エンジニアとして提案できない）
# - 外国籍の可能性が高い
# - 単価が高すぎて案件マッチ不可（100万超）
exclude_names = {
    "K.Y": "コンサル/DX推進PM/単価180万",
    "O.K": "PM/PMO・証券業務30年/単価78万（コンサル系）",
    "TK": "要件定義上流/単価125万（コンサル系）",
    "K.D": "セールスコンサル/単価100万",
    "K.K": "PM/PMO/単価94万（コンサル系）",
    "N.Y": "コンテンツマーケ（エンジニアではない）",
    "王YX（オウ）": "外国籍疑い（除外ルール）",
    "T.T": "VBA/ExcelマクロのみでスキルDB薄い",
    "T.H": "ネットワークエンジニア（スキル未登録）",
}

fixed = 0
for p in eng_all:
    props = p["properties"]
    name = props.get("名前", {}).get("title", [{}])[0].get("plain_text", "?")
    
    if name in exclude_names:
        reason = exclude_names[name]
        # 備考に除外理由を追記し、稼働状況を「調整中」に変更
        note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        old_note = note_items[0].get("plain_text", "") if note_items else ""
        new_note = old_note + f"\n\n【提案除外】{reason}"
        
        r = requests.patch(f"https://api.notion.com/v1/pages/{p['id']}",
            headers=headers, json={"properties": {
                "稼働状況": {"select": {"name": "調整中"}},
                "備考（LINEメモ）": {"rich_text": [{"type": "text", "text": {"content": new_note[:2000]}}]}
            }})
        if r.status_code == 200:
            print(f"  ✓ 除外設定: {name} ({reason})")
            fixed += 1
        else:
            print(f"  ✗ エラー: {name} / {r.status_code}")

print(f"\n除外設定完了: {fixed}件")
print("\n=== 最終状態確認 ===")
from collections import Counter
all_eng = query_db(ENGINEER_DB)
statuses = Counter()
for p in all_eng:
    s = p["properties"].get("稼働状況", {}).get("select", {})
    statuses[s.get("name", "未設定") if s else "未設定"] += 1
for k, v in statuses.items():
    print(f"  {k}: {v}件")
