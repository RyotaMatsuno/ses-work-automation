import os
import subprocess
import time

ses_work = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
log_path = os.path.join(ses_work, "mail_pipeline", "codex_drive.log")
codex_cmd = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

prompt = (
    "Read SPEC_drive.md and CLAUDE_drive.md, then implement all tasks in TASKS_drive.md in order. "
    "Working directory is ses_work/. Target files: mail_pipeline/drive_uploader.py (create new), "
    "mail_pipeline/mail_pipeline.py (patch), matching_v2/notify_line.py (patch). "
    "After all tasks complete, run: python mail_pipeline/drive_uploader.py to smoke test."
)

bat_content = f"""@echo off
cd /d "{ses_work}\\mail_pipeline"
"{codex_cmd}" --dangerously-bypass-approvals-and-sandbox -C "{ses_work}\\mail_pipeline" "{prompt}" > "{log_path}" 2>&1
"""

bat_path = os.path.join(ses_work, "run_codex_drive.bat")
with open(bat_path, "w", encoding="ascii") as f:
    f.write(bat_content)

proc = subprocess.Popen(["cmd", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
print(f"Codex PID: {proc.pid}")
print(f"Log: {log_path}")
time.sleep(5)

# 初期ログ確認
if os.path.exists(log_path):
    size = os.path.getsize(log_path)
    print(f"Log size after 5s: {size} bytes")
    if size > 0:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            print(f.read()[:500])
else:
    print("Log not yet created")
