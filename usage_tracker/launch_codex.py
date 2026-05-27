import subprocess
import sys
import os

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\codex_run.log"

cmd = 'codex exec "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの順番で全タスクを実装してください" --dangerously-bypass-approvals-and-sandbox'

with open(log_path, 'w', encoding='utf-8') as log:
    p = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    )

print(f"Codex started PID={p.pid}", flush=True)
