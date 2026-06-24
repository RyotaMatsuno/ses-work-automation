import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_affiliation.log"
size = os.path.getsize(log)
print(f"webhook Codex log: {size}bytes")
if size > 0:
    with open(log, encoding="utf-8", errors="replace") as f:
        print(f.read()[-500:])

# webhook_server.pyにaffilliationが入ったか確認
wh = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
with open(wh, encoding="utf-8") as f:
    content = f.read()
print(f"\nwebhook has 'affiliation': {'affiliation' in content}")
print(f"webhook has '所属会社': {'所属会社' in content}")
