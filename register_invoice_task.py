import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
r = subprocess.run(
    r'schtasks /create /tn "freee_invoice_send" /tr "\"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe\" \"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\invoice_sender.py\"" /sc monthly /d 1 /st 10:00 /f /rl highest',
    shell=True,
    capture_output=True,
)
print(r.stdout.decode("utf-8", errors="replace"))
print(r.stderr.decode("utf-8", errors="replace"))
# 確認
r2 = subprocess.run('schtasks /query /tn "freee_invoice_send" /fo list', shell=True, capture_output=True)
print(r2.stdout.decode("utf-8", errors="replace")[:400])
