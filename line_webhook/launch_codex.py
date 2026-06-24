import subprocess

log_out = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\codex_exec.log"
log_err = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\codex_exec_err.log"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

with open(log_out, "w") as out, open(log_err, "w") as err:
    proc = subprocess.Popen(
        [
            codex,
            "exec",
            "SPEC.mdとCLAUDE.mdを読んでTASKS.mdの順番で実装してください",
            "--dangerously-bypass-approvals-and-sandbox",
            "-C",
            cwd,
        ],
        cwd=cwd,
        stdout=out,
        stderr=err,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

print(f"Codex PID: {proc.pid}")
