"""mail_fetcher単体テスト - 直近3日分のみ"""
import imaplib
import email
import os
import sys
from email.header import decode_header
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

server = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
port = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
user = os.environ.get("SESSALES_EMAIL")
password = os.environ.get("SESSALES_PASSWORD")

print(f"Connecting to {server}:{port} as {user}...")

try:
    mail = imaplib.IMAP4_SSL(server, port)
    mail.login(user, password)
    print("LOGIN OK")
except Exception as e:
    print(f"LOGIN FAIL: {e}")
    sys.exit(1)

mail.select("INBOX")

# Search last 3 days only
since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
_, data = mail.uid("search", None, f"SINCE {since_date}")
uids = data[0].split()
print(f"Mails in last 3 days: {len(uids)}")

SUPPORTED_EXTS = {".xlsx", ".xls", ".pdf", ".docx", ".doc"}
count = 0

for uid_bytes in uids[:20]:  # Max 20
    uid = uid_bytes.decode()
    _, msg_data = mail.uid("fetch", uid_bytes, "(RFC822)")
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)
    
    subj_parts = decode_header(msg.get("Subject", ""))
    subj = ""
    for part, charset in subj_parts:
        if isinstance(part, bytes):
            subj += part.decode(charset or "utf-8", errors="replace")
        else:
            subj += part
    
    for part in msg.walk():
        cd = part.get("Content-Disposition", "")
        if "attachment" not in cd:
            continue
        fn_raw = part.get_filename()
        if not fn_raw:
            continue
        fn_parts = decode_header(fn_raw)
        fn = ""
        for p, c in fn_parts:
            if isinstance(p, bytes):
                fn += p.decode(c or "utf-8", errors="replace")
            else:
                fn += p
        ext = Path(fn).suffix.lower()
        if ext in SUPPORTED_EXTS:
            size = len(part.get_payload(decode=True) or b"")
            print(f"  [UID={uid}] {fn} ({ext}) {size} bytes | Subj: {subj[:50]}")
            count += 1

mail.logout()
print(f"\nTotal attachments found: {count}")
