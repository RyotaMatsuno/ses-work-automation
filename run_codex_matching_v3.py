import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

codex_path = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\codex_matching_v2.log"

cmd = [
    codex_path,
    "--dangerously-bypass-approvals-and-sandbox",
    "-C",
    cwd,
    "TASKS.mdを読んで残タスクをすべて実装してください。matching_v2.pyのみ修正対象です。",
]

with open(log_path, "w", encoding="utf-8") as log:
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=log,
        cwd=cwd,
        creationflags=0x00000008,  # CREATE_NO_WINDOW
    )

print(f"Codex起動: PID={proc.pid}")
print(f"ログ: {log_path}")
