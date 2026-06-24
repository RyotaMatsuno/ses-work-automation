"""IMAP接続テストのみ"""

import imaplib
import os

from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

server = os.environ.get("OUTLOOK_IMAP_SERVER", "mail65.onamae.ne.jp")
port = int(os.environ.get("OUTLOOK_IMAP_PORT", 993))
user = os.environ.get("SESSALES_EMAIL")
password = os.environ.get("SESSALES_PASSWORD")

print(f"Connecting to {server}:{port}...")
mail = imaplib.IMAP4_SSL(server, port, timeout=30)
print("SSL OK")
mail.login(user, password)
print("LOGIN OK")
mail.select("INBOX")
print("SELECT OK")
# Just count
_, data = mail.search(None, "ALL")
total = len(data[0].split())
print(f"Total mails: {total}")
mail.logout()
print("DONE")
