import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
keys = [
    k
    for k in config
    if "MAIL" in k or "EMAIL" in k or "PASS" in k or "IMAP" in k or "OUTLOOK" in k or "MATSUNO" in k or "OKAMOTO" in k
]
for k in sorted(keys):
    v = config[k]
    if "PASS" in k or "SECRET" in k or "TOKEN" in k:
        print(f"{k}: ***")
    else:
        print(f"{k}: {v}")
