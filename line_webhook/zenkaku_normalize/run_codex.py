import subprocess, sys, os

cmd = [
    r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd",
    "exec",
    "SPEC.mdを読んでTASKS.mdの順番で実装してください。実装対象は ../line_query.py です。",
    "--dangerously-bypass-approvals-and-sandbox"
]

log_path = os.path.join(os.path.dirname(__file__), "codex_run.log")
with open(log_path, "w", encoding="utf-8") as logf:
    proc = subprocess.Popen(
        cmd,
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\zenkaku_normalize",
        stdout=logf, stderr=logf,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

print(f"Codex PID: {proc.pid}")
print(f"Log: {log_path}")
