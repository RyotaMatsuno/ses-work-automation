
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

# 共通アドレスから最新3000件の件名を取得
mail = imaplib.IMAP4_SSL('mail65.onamae.ne.jp', 993, ssl_context=ctx)
mail.login(config['OUTLOOK_EMAIL'], config['OUTLOOK_PASSWORD'])
mail.select('INBOX')
status, messages = mail.search(None, 'ALL')
all_ids = messages[0].split()
target = list(reversed(all_ids))[:3000]
print(f"共通アドレス: 全{len(all_ids)}件 → 最新{len(target)}件取得中...")

subjects = []
for i, mid in enumerate(target):
    try:
        status, msg_data = mail.fetch(mid, '(BODY[HEADER.FIELDS (SUBJECT FROM)])')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subj = decode_str(msg.get('Subject', ''))
        frm = decode_str(msg.get('From', ''))
        subjects.append({'subject': subj, 'from': frm})
    except:
        pass
    if (i+1) % 500 == 0:
        print(f"  {i+1}件処理中...")
mail.logout()

# 松野アドレスからも取得
mail2 = imaplib.IMAP4_SSL('mail65.onamae.ne.jp', 993, ssl_context=ctx)
mail2.login(config['MATSUNO_EMAIL'], config['MATSUNO_PASSWORD'])
mail2.select('INBOX')
status, messages = mail2.search(None, 'ALL')
all_ids2 = messages[0].split()
target2 = list(reversed(all_ids2))[:1000]
print(f"松野アドレス: 全{len(all_ids2)}件 → 最新{len(target2)}件取得中...")

for i, mid in enumerate(target2):
    try:
        status, msg_data = mail2.fetch(mid, '(BODY[HEADER.FIELDS (SUBJECT FROM)])')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subj = decode_str(msg.get('Subject', ''))
        frm = decode_str(msg.get('From', ''))
        subjects.append({'subject': subj, 'from': frm, 'account': 'matsuno'})
    except:
        pass
mail2.logout()

import json
with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_subjects_sample.json', 'w', encoding='utf-8') as f:
    json.dump(subjects, f, ensure_ascii=False, indent=2)
print(f"\n完了: 合計{len(subjects)}件保存")
