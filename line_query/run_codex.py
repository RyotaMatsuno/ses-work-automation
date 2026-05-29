import subprocess, os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\codex_run.log"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query"
codex = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

prompt = "SPEC.mdとCLAUDE.mdを読んでTASKS.mdの順番で全タスクを実装してください。"

with open(log_path, "w", encoding="utf-8") as f:
    proc = subprocess.Popen(
        [codex, "exec", prompt,
         "-C", cwd,
         "--dangerously-bypass-approvals-and-sandbox"],
        stdout=f, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=cwd
    )

print(f"Codex PID: {proc.pid}")
print(f"Log: {log_path}")
