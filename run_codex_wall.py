import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_wall.log'
cwd = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'

proc = subprocess.Popen(
    'codex exec "CLAUDE_wall.mdとSPEC_wall.mdを読んでTASKS_wall.mdの1〜7番を順番に実装してください。完了したタスクは[x]に更新。" --dangerously-bypass-approvals-and-sandbox',
    shell=True, cwd=cwd,
    stdout=open(log, 'w', encoding='utf-8', errors='replace'),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW
)
print(f"Codex PID: {proc.pid}", flush=True)
