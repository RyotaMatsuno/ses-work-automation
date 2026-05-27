import subprocess
import sys

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\codex_run.log"

cmd = 'codex exec "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの順番で全タスクを実装してください" --dangerously-bypass-approvals-and-sandbox'

print("Codex starting...", flush=True)
result = subprocess.run(
    cmd,
    shell=True,
    cwd=cwd,
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace',
    timeout=290
)

output = result.stdout + result.stderr
with open(log_path, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"returncode={result.returncode}", flush=True)
print(output[-2000:], flush=True)
