import sys, requests
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776
h = get_headers()

# 会社情報確認
res = requests.get(f"{FREEE_BASE}/companies", headers=h)
print("会社:", res.json())

# 請求書をパラメータなしで全取得試行
res2 = requests.get(f"{FREEE_BASE}/invoices",
    headers=h,
    params={"company_id": COMPANY_ID, "limit": 100})
print(f"\nステータス: {res2.status_code}")
print(f"レスポンス: {res2.text[:500]}")
