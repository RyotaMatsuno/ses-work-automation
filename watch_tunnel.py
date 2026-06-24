import re
import time

LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\cloudflare\tunnel.log"

for i in range(40):
    time.sleep(1)
    try:
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(f"[{i}s] log size: {len(content)}", flush=True)
        m = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", content)
        if m:
            print(f"URL FOUND: {m.group(0)}", flush=True)
            break
        if content:
            print(content[-300:], flush=True)
    except Exception as e:
        print(f"[{i}s] read error: {e}", flush=True)
