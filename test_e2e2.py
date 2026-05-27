import sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import dotenv_values
config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID", "")

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
from remote_command_handler import get_health

result = get_health()
print(f"health: {result}", flush=True)

msg = f"Jobz Tunnel TEST\n{result}\nURL: https://sessions-bone-immune-mtv.trycloudflare.com"
r = requests.post(
    "https://api.line.me/v2/bot/message/push",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    json={"to": MATSUNO_USER_ID, "messages": [{"type": "text", "text": msg}]},
    timeout=10
)
print(f"LINE push status: {r.status_code}", flush=True)
