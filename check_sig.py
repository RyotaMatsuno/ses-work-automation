# -*- coding: utf-8 -*-
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

idx = content.find("def process_message")
print(content[idx : idx + 120], flush=True)

# MATSUNO_USER_IDとの比較
print("\n=== MATSUNO_USER_ID定義 ===", flush=True)
idx2 = content.find("MATSUNO_USER_ID")
print(content[idx2 : idx2 + 150], flush=True)
