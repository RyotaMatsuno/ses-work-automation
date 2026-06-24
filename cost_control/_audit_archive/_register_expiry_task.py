import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"


def run(cmd, **k):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **k)


# 1. commit Phase 2 (local restore point)
run(
    [
        "git",
        "-C",
        BASE,
        "add",
        "mail_pipeline/mail_pipeline.py",
        "cost_control/project_expiry.py",
        "cost_control/TASKS.md",
    ]
)
c = run(["git", "-C", BASE, "commit", "-m", "cost_control Phase2: broadcast filter + project auto-expiry"])
print("COMMIT:", (c.stdout or c.stderr).splitlines()[-1] if (c.stdout or c.stderr) else "?")

# 2. write ASCII bat using %~dp0 (no Japanese in content)
bat = os.path.join(BASE, "wd_project_expiry.bat")
bat_content = '@echo off\r\ncd /d "%~dp0"\r\npython "%~dp0cost_control\\project_expiry.py" >> "%~dp0cost_control\\project_expiry_task.log" 2>&1\r\n'
with open(bat, "w", encoding="ascii") as f:
    f.write(bat_content)
print("BAT written:", bat)

# 3. write register ps1 (utf-8 BOM so PowerShell reads Japanese path correctly)
ps1 = os.path.join(BASE, "_register_expiry.ps1")
ps = (
    "$ErrorActionPreference='Stop'\r\n"
    f"$bat='{bat}'\r\n"
    "$a=New-ScheduledTaskAction -Execute $bat\r\n"
    "$t=New-ScheduledTaskTrigger -Daily -At 7:00am\r\n"
    "$s=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)\r\n"
    "Register-ScheduledTask -TaskName 'SES_ProjectExpiry' -Action $a -Trigger $t -Settings $s -Force | Out-Null\r\n"
    "Write-Output 'REGISTERED_OK'\r\n"
)
with open(ps1, "w", encoding="utf-8-sig") as f:
    f.write(ps)
r = run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1])
print("PS1 stdout:", (r.stdout or "").strip()[:300])
print("PS1 stderr:", (r.stderr or "").strip()[:300])

# 4. verify
v = run(["schtasks", "/query", "/tn", "SES_ProjectExpiry", "/fo", "list"])
for line in (v.stdout or v.stderr).splitlines():
    if any(k in line for k in ["TaskName", "Next", "Status", "状態", "次回", "タスク名"]):
        print("VERIFY:", line.strip()[:120])
print("DONE")
