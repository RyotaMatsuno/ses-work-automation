import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# VAL_ACTIVE2/VAL_ADJUSTING の実際の値を確認
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# project_queryの中身確認
idx = src.find("def project_query")
print(src[idx : idx + 600])
print()

# VAL_ACTIVE2, VAL_ADJUSTING の値確認
val2 = bytes.fromhex("e7a8bce5838de58fafe883bd").decode()
val3 = bytes.fromhex("e8aabfe695b4e4b8ad").decode()
print(f'VAL_ACTIVE2   = "{val2}"')
print(f'VAL_ADJUSTING = "{val3}"')
