# どちらもASCIIのみ（BATに日本語を入れない＝文字化け回避）。日本語パスは %~dp0 で実行時解決。

bat1 = (
    "@echo off\r\n"
    'cd /d "%~dp0.."\r\n'
    "set PYTHONIOENCODING=utf-8\r\n"
    "py freee\\freee_invoice_monthly.py --execute >> freee\\monthly_invoice.log 2>&1\r\n"
)

bat2 = (
    "@echo off\r\n"
    "REM Run AFTER freee_invoice_monthly.py exists (post-Codex). Registers monthly draft task.\r\n"
    'schtasks /Create /TN "TERRA_Monthly_Invoice" /TR "\\"%~dp0run_monthly_invoice.bat\\"" /SC MONTHLY /D 1 /ST 09:30 /RL LIMITED /F\r\n'
    'schtasks /Query /TN "TERRA_Monthly_Invoice"\r\n'
)

base = r"C:\Users\ma_py\OneDrive\\\u30c7\u30b9\u30af\u30c8\u30c3\u30d7\ses_work\freee"
import os

base = os.path.join(os.environ["USERPROFILE"], "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work", "freee")
p1 = os.path.join(base, "run_monthly_invoice.bat")
p2 = os.path.join(base, "register_monthly_task.bat")
with open(p1, "w", encoding="ascii", newline="") as f:
    f.write(bat1)
with open(p2, "w", encoding="ascii", newline="") as f:
    f.write(bat2)
print("created:", p1)
print("created:", p2)
print("--- run_monthly_invoice.bat ---")
print(bat1)
print("--- register_monthly_task.bat ---")
print(bat2)
