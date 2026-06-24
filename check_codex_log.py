import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\reply_parser\codex_reply_parser.log"
if os.path.exists(log):
    with open(log, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    # 末尾500文字
    print(content[-1000:] if len(content) > 1000 else content)
else:
    print("logなし")
