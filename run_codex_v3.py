import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

proc = subprocess.Popen(
    [
        CODEX,
        "exec",
        "SPEC.mdを読んでTASKS.mdの順番でmatching_v2/の精度改善を実装してください",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    ],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    stdout=open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_v3.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print(f"Codex PID: {proc.pid}", flush=True)
