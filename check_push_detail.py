# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# handle_line_queryのpush_message呼び出し部分を詳細に
idx = content.find("handle_line_query")
snippet = content[idx : idx + 600]
print(snippet, flush=True)
