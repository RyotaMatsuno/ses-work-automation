import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
import requests
from token_manager import get_headers

FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776

h = get_headers()
print("token取得OK")

# 取引先一覧で疎通確認
r = requests.get(
    f"{FREEE_BASE}/partners",
    headers={**h, "Content-Type": "application/json"},
    params={"company_id": COMPANY_ID, "keyword": "TERRA"},
)
print(f"partners API: {r.status_code}")
if r.status_code == 200:
    partners = r.json().get("partners", [])
    print(f"  取引先ヒット: {len(partners)}件")
    for p in partners[:3]:
        print(f"  - {p.get('name')} id={p.get('id')}")
else:
    print(f"  エラー: {r.text[:300]}")
