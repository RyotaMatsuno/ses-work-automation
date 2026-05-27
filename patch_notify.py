import re

filepath = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\notify_line.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: timeout=10 -> timeout=30 in get_assignee and get_page_info
content = content.replace("timeout=10,\n    )", "timeout=30,\n    )")

# Fix 2: OKAMOTO channel token fallback
old = '''        OKAMOTO: {
            "channel_token": os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
            "user_id": os.environ.get("OKAMOTO_LINE_USER_ID", ""),
        },'''
new = '''        OKAMOTO: {
            "channel_token": os.environ.get("OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN") or os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
            "user_id": os.environ.get("OKAMOTO_LINE_USER_ID", ""),
        },'''
content = content.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied.")

# Verify
with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if "timeout" in line or "OKAMOTO_LINE_CHANNEL" in line:
        print(f"L{i}: {line.rstrip()}")
