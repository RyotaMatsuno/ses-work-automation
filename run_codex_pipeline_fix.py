import subprocess

codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
spec_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_notify_fix"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_pipeline_fix.log"

instruction = "Read SPEC.md and implement all tasks in TASKS.md in order. Target files are in the parent directory (ses_work/). Mark each task done in TASKS.md as you complete it."

proc = subprocess.Popen(
    [codex, "--dangerously-bypass-approvals-and-sandbox", "-C", spec_dir, instruction],
    stdout=open(log_path, "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=0x00000008,
)
print(f"Codex PID: {proc.pid}")
print(f"Log: {log_path}")
