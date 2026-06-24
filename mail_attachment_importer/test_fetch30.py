"""mail_fetcher単体テスト - 直近30日・添付ありのみ"""

import email
import imaplib
import os
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

server = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
port = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
user = os.environ.get("SESSALES_EMAIL")
passwd = os.environ.get("SESSALES_PASSWORD")

print(f"Connecting {server}:{port} as {user} ...")
try:
    mail = imaplib.IMAP4_SSL(server, port, timeout=20)
    mail.login(user, passwd)
    print("LOGIN OK")
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)

mail.select("INBOX")
since = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
_, data = mail.uid("search", None, f"SINCE {since}")
uids = data[0].split() if data[0] else []
print(f"Mails since {since}: {len(uids)}")

EXTS = {".xlsx", ".xls", ".pdf", ".docx", ".doc"}
found = []


def dec(v):
    if not v:
        return ""
    parts = decode_header(v)
    out = []
    for p, c in parts:
        out.append(p.decode(c or "utf-8", errors="replace") if isinstance(p, bytes) else p)
    return "".join(out)


for ub in uids:
    uid = ub.decode()
    try:
        _, md = mail.uid("fetch", ub, "(RFC822)")
        msg = email.message_from_bytes(md[0][1])
        for part in msg.walk():
            if "attachment" not in part.get("Content-Disposition", ""):
                continue
            fn = dec(part.get_filename())
            if not fn:
                continue
            ext = Path(fn).suffix.lower()
            if ext not in EXTS:
                continue
            size = len(part.get_payload(decode=True) or b"")
            found.append((uid, fn, ext, size, dec(msg.get("Subject", ""))))
    except Exception as e:
        print(f"  skip uid={uid}: {e}")

mail.logout()
print(f"\n=== Found {len(found)} attachments ===")
for uid, fn, ext, size, subj in found[:10]:
    print(f"  [{uid}] {fn} ({ext}) {size}B | {subj[:40]}")
if len(found) > 10:
    print(f"  ... and {len(found) - 10} more")
