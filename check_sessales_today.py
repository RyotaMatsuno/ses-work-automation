# -*- coding: utf-8 -*-
import email
import imaplib
import ssl
import sys
from datetime import datetime
from email.header import decode_header

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

mail = imaplib.IMAP4_SSL("mail65.onamae.ne.jp", 993, ssl_context=ctx)
mail.login(env.get("OUTLOOK_EMAIL"), env.get("OUTLOOK_PASSWORD"))
mail.select("INBOX")

today_str = datetime.now().strftime("%d-%b-%Y")
_, msgs = mail.search(None, f"SINCE {today_str}")
ids = msgs[0].split() if msgs[0] else []
print(f"今日のsessales受信: {len(ids)}件")
print()

# 末尾30件の件名だけ確認（最新のもの）
sample_ids = list(reversed(ids[-30:]))
print("最新30件の件名（案件かどうか目視確認用）:")
for mid in sample_ids[:30]:
    try:
        _, data = mail.fetch(mid, "(RFC822.HEADER)")
        msg = email.message_from_bytes(data[0][1])
        subj_raw = msg.get("Subject", "")
        parts = decode_header(subj_raw)
        subj = ""
        for part, charset in parts:
            if isinstance(part, bytes):
                subj += part.decode(charset or "utf-8", errors="replace")
            else:
                subj += str(part)
        print(f"  {subj[:70]}")
    except:
        pass

mail.logout()
