import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
os.chdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

from line_query import handle_line_query

print("=== ローカルで 'HS 北小金' を実行（修正後コード） ===")
result = handle_line_query("HS 北小金")
if result:
    print(result)
else:
    print("(no result)")

print("\n\n=== 'H.S 北小金' も試す ===")
result2 = handle_line_query("H.S 北小金")
if result2:
    print(result2)
else:
    print("(no result)")
