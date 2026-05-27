
import sys, imaplib, ssl
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values

config = dotenv_values(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

accounts = [
    {'user': config['OUTLOOK_EMAIL'], 'pass': config['OUTLOOK_PASSWORD'], 'label': '共通'},
    {'user': config['MATSUNO_EMAIL'], 'pass': config['MATSUNO_PASSWORD'], 'label': '松野'},
]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

for acc in accounts:
    try:
        mail = imaplib.IMAP4_SSL('mail65.onamae.ne.jp', 993, ssl_context=ctx)
        mail.login(acc['user'], acc['pass'])
        mail.select('INBOX')
        status, messages = mail.search(None, 'ALL')
        count = len(messages[0].split()) if messages[0] else 0
        print(f"[OK] {acc['label']} ({acc['user']}): INBOX {count}件")
        mail.logout()
    except Exception as e:
        print(f"[NG] {acc['label']} ({acc['user']}): {e}")
