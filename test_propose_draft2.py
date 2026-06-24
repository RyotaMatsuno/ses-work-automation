import imaplib
import ssl
import sys
import time
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env_path = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
env = {}
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip().strip('"').strip("'")

from_email = env.get("SESSALES_EMAIL", "sessales@terra-ltd.co.jp")
password = env.get("SESSALES_PASSWORD")

# MIMEText で日本語subjectをRFC2047エンコード
msg = MIMEText("これはpropose_pipelineのDraft保存テストです。", "plain", "utf-8")
msg["Subject"] = Header("【テスト】propose_pipeline Draft保存確認", "utf-8")
msg["From"] = from_email
msg["To"] = from_email
msg["Date"] = formatdate(localtime=True)
msg["Message-ID"] = make_msgid()

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
try:
    with imaplib.IMAP4_SSL("mail65.onamae.ne.jp", 993, ssl_context=ctx) as mail:
        mail.login(from_email, password)
        status, _ = mail.append("Drafts", "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
        print(f"APPEND status: {status}")
        print("Draft保存成功" if status == "OK" else "Draft保存失敗")
except Exception as e:
    print(f"エラー: {e}")
