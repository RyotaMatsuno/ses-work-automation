import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import os

# 環境変数設定
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

# 最新のline_queryでテスト
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

if "line_query" in sys.modules:
    del sys.modules["line_query"]
from line_query import classify_query, handle_line_query

print("=== 全パターンテスト ===")
test_cases = [
    ("HS 北小金", "engineer"),
    ("H.S 北小金", "engineer"),  # ドット付き対応
    ("H.S　北小金", "engineer"),  # 全角スペース
    ("hs 北小金", "engineer"),  # 小文字
    # 50文字超はNoneを返すことを確認
    ("Web系のJAVA案件ありましたらお願いします！長期案件リモート希望", "None"),
]

for tc, expected_type in test_cases:
    qtype, params = classify_query(tc)
    result = handle_line_query(tc)

    if expected_type == "None":
        status = "✅" if result is None else "❌"
        print(f"{status} [{tc[:20]}...] → {result is None and 'None(スルー)' or f'予期しない結果: {str(result)[:50]}'}")
    elif expected_type == "engineer":
        status = "✅" if qtype == "engineer" else "❌"
        print(f"{status} [{tc}] classify={qtype}/{params}")
        if result:
            first_line = result.split("\n")[0]
            print(f"   返答1行目: {first_line}")
    print()

print()
print("=== H.S 北小金 の実際の返答（最初500文字） ===")
result = handle_line_query("HS 北小金")
if result:
    print(result[:800])
else:
    print("None")
