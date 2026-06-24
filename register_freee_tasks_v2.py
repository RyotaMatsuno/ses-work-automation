import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# /rl highest なしで登録を試みる（通常権限で登録）
PYTHON = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

tasks = [
    {
        "name": "freee_invoice_send",
        "script": rf"{BASE}\freee\invoice_sender.py",
        "schedule": "/sc monthly /d 1 /st 10:00",
        "desc": "毎月1日 10:00 請求書自動送付",
    },
    {
        "name": "freee_payment_check",
        "script": rf"{BASE}\freee\payment_checker.py",
        "schedule": "/sc monthly /d 10 /st 08:00",
        "desc": "毎月10日 08:00 入金確認",
    },
    {
        "name": "freee_payment_check_20",
        "script": rf"{BASE}\freee\payment_checker.py",
        "schedule": "/sc monthly /d 20 /st 08:00",
        "desc": "毎月20日 08:00 入金確認",
    },
    {
        "name": "freee_payment_check_28",
        "script": rf"{BASE}\freee\payment_checker.py",
        "schedule": "/sc monthly /d 28 /st 08:00",
        "desc": "毎月28日 08:00 入金確認",
    },
]

for t in tasks:
    cmd = f'schtasks /create /tn "{t["name"]}" /tr "\\"{PYTHON}\\" \\"{t["script"]}\\"" {t["schedule"]} /f'
    r = subprocess.run(cmd, shell=True, capture_output=True)
    out = r.stdout.decode("utf-8", errors="replace").strip()
    err = r.stderr.decode("utf-8", errors="replace").strip()
    status = "OK" if r.returncode == 0 else "NG"
    print(f"[{status}] {t['name']} ({t['desc']})")
    if out:
        print(f"  OUT: {out[:80]}")
    if err:
        print(f"  ERR: {err[:80]}")
