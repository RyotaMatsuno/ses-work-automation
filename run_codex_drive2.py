
import subprocess, os, time, sys

ses_work = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
pipeline_dir = os.path.join(ses_work, "mail_pipeline")
log_path = os.path.join(pipeline_dir, "codex_drive.log")
codex_cmd = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

prompt = (
    "Read SPEC_drive.md and CLAUDE_drive.md, then implement all tasks in TASKS_drive.md in order. "
    "Working directory is the parent ses_work directory. "
    "Create mail_pipeline/drive_uploader.py (new file), "
    "patch mail_pipeline/mail_pipeline.py, "
    "patch matching_v2/notify_line.py. "
    "After all tasks, run: python mail_pipeline/drive_uploader.py to smoke test."
)

with open(log_path, "w", encoding="utf-8") as f:
    f.write("")

proc = subprocess.Popen(
    [codex_cmd, "--dangerously-bypass-approvals-and-sandbox", "-C", pipeline_dir, prompt],
    stdout=open(log_path, "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    cwd=ses_work,
)
print(f"Codex PID: {proc.pid}")
print(f"Log: {log_path}")
time.sleep(8)

size = os.path.getsize(log_path)
print(f"Log size after 8s: {size} bytes")
if size > 0:
    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
        print(f.read()[:800])
else:
    print("Log still empty - Codex starting up...")
