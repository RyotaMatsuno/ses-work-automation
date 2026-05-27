
import sys, imaplib, ssl, email
from email.header import decode_header
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
import pathlib

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

SKILL_EXT = {'.pdf', '.docx', '.doc', '.xlsx', '.xls'}

def get_attachments(msg):
    files = []
    for part in msg.walk():
        fname_raw = part.get_filename()
        if not fname_raw: continue
        fname = decode_str(fname_raw)
        ext = pathlib.Path(fname).suffix.lower()
        if ext in SKILL_EXT:
            files.append(fname)
    return files

# 松野個人アドレス最新300件を調査
mail = imaplib.IMAP4_SSL('mail65.onamae.ne.jp', 993, ssl_context=ctx)
mail.login(config['MATSUNO_EMAIL'], config['MATSUNO_PASSWORD'])
mail.select('INBOX')
status, messages = mail.search(None, 'ALL')
all_ids = messages[0].split()
target = list(reversed(all_ids))[:300]
print(f"松野個人アドレス最新300件調査中...")

attach_mails = []
for i, mid in enumerate(target):
    try:
        status, msg_data = mail.fetch(mid, '(RFC822)')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subj = decode_str(msg.get('Subject', ''))
        frm = decode_str(msg.get('From', ''))
        files = get_attachments(msg)
        if files:
            attach_mails.append({'subject': subj[:80], 'from': frm[:60], 'files': files})
    except: pass
mail.logout()

print(f"\n添付ありメール: {len(attach_mails)}件 / 300件中")
print(f"\n=== 全件表示 ===")
for m in attach_mails:
    print(f"FILE: {m['files']}")
    print(f"SUBJ: {m['subject']}")
    print(f"FROM: {m['from']}")
    print()
