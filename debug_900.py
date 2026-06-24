import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

# 900万の異常データを調査
config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 案件名「大手総合商社様向けMicrosoft Azure」を検索
r = requests.post(
    f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
    headers=headers,
    json={"page_size": 5, "filter": {"property": "ステータス", "select": {"equals": "募集中"}}},
    timeout=15,
)
pages = r.json().get("results", [])

print("=== 上位案件の単価確認 ===")
# 単価が高い順に確認
rates = []
for p in pages:
    props = p.get("properties", {})
    name_t = props.get("案件名", {}).get("title", [])
    name = "".join(t.get("plain_text", "") for t in name_t)
    rate = props.get("単価（万円）", {}).get("number", 0) or 0
    req = [o["name"] for o in props.get("必要スキル", {}).get("multi_select", [])]
    rates.append((rate, name, req))

rates.sort(reverse=True)
for rate, name, req in rates[:5]:
    print(f"  {rate}万: {name[:40]} req={req}")

print()
print("=== 問題の診断 ===")
print("900万・800万・750万の案件が上位に来ている")
print("→ スキルフィルタなし案件のgross = 900-70 = 830万")
print("→ 粗利降順ソートで先頭に来てしまう")
print()
print("=== 修正方針 ===")
print("BUG-9修正で PROP_RATE>=75 フィルタを外したが")
print("スキル空案件のgross>=10フィルタも残っているはず")
print("→ gross<10 ではなく gross<thresh で弾いているが thresh=3 or 5")
print("→ gross=830 > thresh=5 なのでパス → 問題")
print()
print("根本原因: スキル空案件をgross>=10で弾く条件があるが")
print("  900万案件のgross=830 >= 10 → 通過してしまう")
print()
print("修正: スキル空案件は除外する（スキルなし案件はマッチング対象外）")
