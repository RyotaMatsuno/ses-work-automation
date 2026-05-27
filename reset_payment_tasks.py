import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 既存3タスク削除
delete_tasks = ["freee_payment_check", "freee_payment_check_20", "freee_payment_check_28"]
for name in delete_tasks:
    r = subprocess.run(f'schtasks /delete /tn "{name}" /f', shell=True, capture_output=True)
    status = "削除OK" if r.returncode == 0 else "NG"
    print(f"[{status}] {name}")

PYTHON = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
SCRIPT = rf"{BASE}\freee\payment_checker.py"

# 月15日・月末（28日）の2本で再登録
new_tasks = [
    ("freee_payment_check_15", "/sc monthly /d 15 /st 08:00", "毎月15日 08:00"),
    ("freee_payment_check_eom", "/sc monthly /d 28 /st 08:00", "毎月28日 08:00（月末代替）"),
]
for name, schedule, desc in new_tasks:
    cmd = f'schtasks /create /tn "{name}" /tr "\\"{PYTHON}\\" \\"{SCRIPT}\\"" {schedule} /f'
    r = subprocess.run(cmd, shell=True, capture_output=True)
    status = "登録OK" if r.returncode == 0 else "NG"
    print(f"[{status}] {name} ({desc})")
