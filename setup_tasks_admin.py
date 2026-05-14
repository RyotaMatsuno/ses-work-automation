import subprocess
import sys
import ctypes

# Check if running as admin
if not ctypes.windll.shell32.IsUserAnAdmin():
    print("Admin required. Relaunching...")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}"', None, 1)
    sys.exit(0)

tasks = [
    ("SES_Outlook_9h",  "09:00", "daily"),
    ("SES_Outlook_13h", "13:00", "daily"),
    ("SES_Outlook_18h", "18:00", "daily"),
]

base = "C:\\Users\\ma_py\\OneDrive\\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\\ses_work"

for name, st, sc in tasks:
    script = f'{base}\\outlook\\outlook_to_notion.py'
    r = subprocess.run(
        ["schtasks", "/create", "/tn", name, "/tr", f'py "{script}"', "/sc", sc, "/st", st, "/f"],
        capture_output=True, text=True
    )
    print(f"{'OK' if r.returncode==0 else 'FAIL'}: {name} - {r.stdout.strip() or r.stderr.strip()}")

# Freee
r = subprocess.run(
    ["schtasks", "/create", "/tn", "SES_Freee_Invoice", "/tr",
     f'py "{base}\\freee\\freee_invoice.py"',
     "/sc", "monthly", "/d", "25", "/st", "10:00", "/f"],
    capture_output=True, text=True
)
print(f"{'OK' if r.returncode==0 else 'FAIL'}: SES_Freee_Invoice - {r.stdout.strip() or r.stderr.strip()}")

input("\nDone! Press Enter to close.")
