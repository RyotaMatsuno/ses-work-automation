# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# _limit_reply関数の全体を抽出
idx = content.find("def _limit_reply")
if idx >= 0:
    # 次のdef or EOFまで
    next_def = content.find("\ndef ", idx + 10)
    snippet = content[idx:next_def] if next_def > 0 else content[idx : idx + 500]
    print(snippet, flush=True)
else:
    print("_limit_reply not found", flush=True)
