import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
import requests
from token_manager import get_headers

h = {**get_headers(), "Content-Type": "application/json"}
COMPANY_ID = 11712776

# freee会計ベースURLのバリエーション確認
bases = [
    "https://api.freee.co.jp/api/1",
    "https://api.freee.co.jp/api/1/",
]

for base in bases:
    url = f"{base}/invoices"
    # GETは200だったのでURLは合ってる
    # OPTIONSでメソッド確認
    r = requests.options(url, headers=h, params={"company_id": COMPANY_ID})
    print(f"OPTIONS {url}: {r.status_code} Allow={r.headers.get('Allow', '')}")

# トークンのスコープ確認
print("\n=== token info ===")
from token_manager import TokenManager

tm = TokenManager()
token_data = tm._load_token()
print(f"scope: {token_data.get('scope', '')}")
print(f"expires_in: {token_data.get('expires_in', '')}")
print(f"token_type: {token_data.get('token_type', '')}")
