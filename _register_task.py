import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

bat = r"""@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
python task_auto_runner\runner.py >> task_auto_runner\logs\bat_run.log 2>&1
"""
with open("task_auto_runner/run_auto_runner.bat", "w", encoding="cp932") as f:
    f.write(bat)
print("bat written")

# タスクスケジューラ登録
import subprocess

bat_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\task_auto_runner\run_auto_runner.bat"
cmd = [
    "schtasks",
    "/create",
    "/tn",
    "SES_TaskAutoRunner",
    "/tr",
    f'"{bat_path}"',
    "/sc",
    "MINUTE",
    "/mo",
    "5",
    "/f",
]
result = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("returncode:", result.returncode)
