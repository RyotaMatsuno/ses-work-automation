import sys
print("step1: import完了", flush=True)

import ssl
print("step2: ssl import完了", flush=True)

import imaplib
print("step3: imaplib import完了", flush=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
print("step4: ssl context作成完了", flush=True)

try:
    mail = imaplib.IMAP4_SSL('mail65.onamae.ne.jp', 993, ssl_context=ctx)
    print("step5: IMAP接続OK", flush=True)
    mail.logout()
except Exception as e:
    print(f"step5 エラー: {e}", flush=True)
