path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\freee_invoice_v2.py"

with open(path, encoding="utf-8") as f:
    src = f.read()

# 1. FREEE_BASE定数を2つに分割
old = 'FREEE_BASE = "https://api.freee.co.jp/api/1"'
new = (
    'FREEE_BASE_ACCT = "https://api.freee.co.jp/api/1"       # 会計API（取引先など）\n'
    'FREEE_BASE_INV  = "https://api.freee.co.jp/invoice/v1"  # 請求書API\n'
    "FREEE_BASE = FREEE_BASE_ACCT  # 後方互換性"
)
src = src.replace(old, new)

# 2. create_invoice内のPOST invoicesをINVに変更
old2 = '    res = requests.post(f"{FREEE_BASE}/invoices", headers=freee_headers(), json=payload)'
new2 = '    res = requests.post(f"{FREEE_BASE_INV}/invoices", headers=freee_headers(), json=payload)'
src = src.replace(old2, new2)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

# 確認
import py_compile

py_compile.compile(path)
print("OK: syntax check passed")

# 変更箇所を表示
for i, line in enumerate(src.splitlines(), 1):
    if "FREEE_BASE" in line or "invoice/v1" in line:
        print(f"  L{i}: {line.strip()}")
