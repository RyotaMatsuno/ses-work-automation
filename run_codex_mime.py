import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CODEX = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_mime.log"

proc = subprocess.Popen(
    [
        CODEX,
        "exec",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_mime_spec\SPEC.mdを読んでTASKS.mdの順番でmail_mcp/mail_server.pyにMIME添付対応を実装してください",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    ],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    stdout=open(log_path, "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print(f"Codex MIME PID: {proc.pid}", flush=True)
