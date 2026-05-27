
import sys, imaplib, ssl, email
from email.header import decode_header
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
from datetime import datetime

config = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def decode_str(s):
    if not s: return ""
    parts = decode_header(s)
    result = ""
    for part, charset in parts:
        if isinstance(part, bytes):
            result += part.decode(charset or 'utf-8', errors='replace')
        else:
            result += str(part)
    return result

# 共通アドレスの最新20件
mail = imaplib.IMAP4_SSL('mail65.onamae.ne.jp', 993, ssl_context=ctx)
mail.login(config['OUTLOOK_EMAIL'], config['OUTLOOK_PASSWORD'])
mail.select('INBOX')
today_str = datetime.now().strftime("%d-%b-%Y")
status, messages = mail.search(None, f'SINCE {today_str}')
all_ids = messages[0].split()
print(f"共通 本日分: {len(all_ids)}件 - 最新20件:")
for mid in list(reversed(all_ids))[:20]:
    status, msg_data = mail.fetch(mid, '(BODY[HEADER.FIELDS (SUBJECT FROM TO)])')
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)
    subj = decode_str(msg.get('Subject', ''))
    frm = decode_str(msg.get('From', ''))
    to = decode_str(msg.get('To', ''))
    print(f"  FROM: {frm[:50]}")
    print(f"  TO:   {to[:50]}")
    print(f"  SUBJ: {subj[:60]}")
    print()
mail.logout()
