
import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
send_mail_py = os.path.join(base, "outreach_system", "send_mail.py")
with open(send_mail_py, encoding="utf-8") as f:
    content = f.read()
print(content[:2000])
