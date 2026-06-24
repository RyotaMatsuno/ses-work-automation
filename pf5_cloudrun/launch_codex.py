import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ses_work = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
log_path = rf"{ses_work}\pf5_cloudrun\codex.log"

cmd = [
    codex,
    "exec",
    "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの順番で実装してください",
    "-C",
    rf"{ses_work}\pf5_cloudrun",
    "--dangerously-bypass-approvals-and-sandbox",
]

with open(log_path, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, cwd=ses_work, creationflags=subprocess.CREATE_NO_WINDOW)

print(f"Codex PID={proc.pid}")
print(f"log: {log_path}")
