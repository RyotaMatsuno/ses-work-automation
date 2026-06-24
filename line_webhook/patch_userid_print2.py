path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = 'MATSUNO_USER_ID = user_id\n\n            if os.path.exists(ENV_PATH):\n\n                set_key(ENV_PATH, "MATSUNO_LINE_USER_ID", user_id)'
new = 'MATSUNO_USER_ID = user_id\n\n            print(f"[userId-matsuno] {user_id}", flush=True)\n\n            if os.path.exists(ENV_PATH):\n\n                set_key(ENV_PATH, "MATSUNO_LINE_USER_ID", user_id)'

if old in content:
    content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCHED OK")
else:
    print("NOT FOUND")
