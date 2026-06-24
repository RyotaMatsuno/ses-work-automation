# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# process_messageの呼び出し箇所を確認
idx = content.find("process_message(msg[")
if idx >= 0:
    print("=== process_message呼び出し ===", flush=True)
    print(content[max(0, idx - 100) : idx + 200], flush=True)

# handle_line_query周辺のuser_id使用箇所
idx2 = content.find("handle_line_query")
if idx2 >= 0:
    print("\n=== handle_line_query周辺 ===", flush=True)
    print(content[max(0, idx2 - 200) : idx2 + 400], flush=True)
