import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
time.sleep(90)
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\codex_payment_checker.log"
with open(log, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()
# 完了報告部分だけ抽出
if "完了報告" in content:
    idx = content.index("完了報告")
    print(content[idx : idx + 1000])
else:
    print(content[-800:])
