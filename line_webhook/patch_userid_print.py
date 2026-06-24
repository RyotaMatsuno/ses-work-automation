path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 検索
target = "MATSUNO_USER_ID = user_id"
idx = content.find(target)
print(f"idx={idx}")
if idx >= 0:
    snippet = content[idx : idx + 200]
    print(repr(snippet))
