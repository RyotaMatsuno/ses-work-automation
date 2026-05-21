
# -*- coding: utf-8 -*-
import requests, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
PROJECT_DB  = '343450ff-37c0-81e4-934e-f25f90284a3c'
ENGINEER_DB = '343450ff-37c0-819d-8769-fb0a8a4ceeb1'

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def query_db(db_id, filter_obj=None):
    results, payload = [], {"page_size": 100}
    if filter_obj: payload["filter"] = filter_obj
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                         headers=headers, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"): break
        payload["start_cursor"] = data["next_cursor"]
    return results

def update_page(page_id, properties):
    r = requests.patch(f"https://api.notion.com/v1/pages/{page_id}",
                      headers=headers, json={"properties": properties})
    return r.status_code, r.json()

fixed = 0
errors = 0

# ===== 1. エンジニアDB 単価バグ修正 =====
eng_all = query_db(ENGINEER_DB)
print("=== エンジニア単価バグ修正 ===")
for p in eng_all:
    props = p["properties"]
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    if price >= 1000:
        corrected = round(price / 10000)
        name = props.get("名前", {}).get("title", [{}])[0].get("plain_text", "?")
        status, _ = update_page(p["id"], {"単価（万円）": {"number": corrected}})
        if status == 200:
            print(f"  ✓ {name}: {price} -> {corrected}万")
            fixed += 1
        else:
            print(f"  ✗ {name}: エラー {status}")
            errors += 1

# ===== 2. 案件DB 単価バグ修正 & ステータス整理 =====
proj_all = query_db(PROJECT_DB)
print("\n=== 案件DB 単価バグ修正 & ステータス整理 ===")

# テスト案件の名前（削除対象）
test_names = ["テスト】Java案件_自動登録確認", "テスト]Javaバックエンド案件"]

for p in proj_all:
    props = p["properties"]
    name = props.get("案件名", {}).get("title", [{}])[0].get("plain_text", "?")
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    status_obj = props.get("ステータス", {}).get("select", {})
    current_status = status_obj.get("name", "") if status_obj else ""
    
    update_props = {}
    
    # テスト案件はゴミ箱へ
    is_test = any(t in name for t in test_names)
    if is_test:
        r = requests.patch(f"https://api.notion.com/v1/pages/{p['id']}",
                          headers=headers, json={"archived": True})
        print(f"  🗑 削除: {name}")
        fixed += 1
        continue
    
    # 単価バグ修正
    if price >= 1000:
        update_props["単価（万円）"] = {"number": round(price / 10000)}
    
    # 「募集中」→「稼働中」に変更
    if current_status == "募集中":
        update_props["ステータス"] = {"select": {"name": "稼働中"}}
    
    if update_props:
        status, _ = update_page(p["id"], update_props)
        changes = []
        if "単価（万円）" in update_props:
            changes.append(f"単価:{price}->{update_props['単価（万円）']['number']}万")
        if "ステータス" in update_props:
            changes.append("募集中->稼働中")
        if status == 200:
            print(f"  ✓ {name[:30]}: {', '.join(changes)}")
            fixed += 1
        else:
            print(f"  ✗ {name[:30]}: エラー {status}")
            errors += 1
    else:
        print(f"  - {name[:30]}: 変更なし")

# ===== 3. 除外対象エンジニアの特定（外国籍・PM/コンサル） =====
print("\n=== 除外対象エンジニア（要確認） ===")
# 外国籍の可能性が高い名前パターン or PM/コンサル系のnote
exclude_candidates = []
for p in eng_all:
    props = p["properties"]
    name = props.get("名前", {}).get("title", [{}])[0].get("plain_text", "?")
    note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
    note = note_items[0].get("plain_text", "").lower() if note_items else ""
    
    reasons = []
    # 外国籍チェック（明記されているもの）
    if "外国籍" in note or ("王" in name and "日本" not in note):
        reasons.append("外国籍疑い")
    # コンサル/PMO系
    if any(kw in note for kw in ["コンサル", "pmo", "セールスコンサル", "コンテンツマーケ"]):
        reasons.append("コンサル/PMO系")
    # 単価が高すぎる（100万超）
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    corrected = round(price/10000) if price >= 1000 else price
    if corrected >= 100:
        reasons.append(f"単価{corrected}万（高すぎ）")
    
    if reasons:
        exclude_candidates.append({"name": name, "reasons": reasons})
        print(f"  ⚠ {name}: {', '.join(reasons)}")

print(f"\n完了: 修正={fixed}件 エラー={errors}件")
print(f"要確認の除外候補: {len(exclude_candidates)}件")
