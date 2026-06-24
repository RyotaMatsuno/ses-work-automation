import imaplib
import ssl
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

accounts = [
    {"user": config["OUTLOOK_EMAIL"], "pass": config["OUTLOOK_PASSWORD"], "label": "共通"},
    {"user": config["MATSUNO_EMAIL"], "pass": config["MATSUNO_PASSWORD"], "label": "松野"},
]

today_str = datetime.now().strftime("%d-%b-%Y")
print(f"当日({today_str})の受信数:")
for acc in accounts:
    try:
        mail = imaplib.IMAP4_SSL("mail65.onamae.ne.jp", 993, ssl_context=ctx)
        mail.login(acc["user"], acc["pass"])
        mail.select("INBOX")
        status, messages = mail.search(None, f"SINCE {today_str}")
        count = len(messages[0].split()) if messages[0] else 0
        print(f"  {acc['label']} ({acc['user']}): {count}件")
        mail.logout()
    except Exception as e:
        print(f"  [NG] {acc['label']}: {e}")
