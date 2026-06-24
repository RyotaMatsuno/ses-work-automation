import imaplib
import json
import os
import socket
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

PROCESSED = Path("processed_ids.json")
socket.setdefaulttimeout(30)

password = os.environ.get("SESSALES_MAIL_PASSWORD") or os.environ.get("OUTLOOK_PASSWORD", "")
server = os.environ.get("IMAP_HOST") or "118.27.122.112"
mail = imaplib.IMAP4_SSL(server, 993)
mail.login("sessales@terra-ltd.co.jp", password)
mail.select("INBOX")

since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
_, data = mail.uid("search", None, f'(SINCE "{since}")')
uids = [u.decode() for u in (data[0].split() if data[0] else [])]
mail.logout()

ids = json.load(open(PROCESSED, "r", encoding="utf-8"))
if not isinstance(ids, dict):
    ids = {"sessales": [], "matsuno": [], "okamoto": []}
ids.setdefault("sessales", [])
before = len(ids["sessales"])
existing = set(ids["sessales"])
for u in uids:
    if u not in existing:
        ids["sessales"].append(u)
        existing.add(u)
after = len(ids["sessales"])
json.dump(ids, open(PROCESSED, "w", encoding="utf-8"), ensure_ascii=False)
print(f"BEFORE={before} AFTER={after} ADDED={after - before}")
