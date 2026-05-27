import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_wall_v2.log'
cwd = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'

proc = subprocess.Popen(
    'codex exec "SPEC_wall_v2.mdを読んでTASKS_wall_v2.mdの1〜5番を実装してください。" --dangerously-bypass-approvals-and-sandbox',
    shell=True, cwd=cwd,
    stdout=open(log, 'w', encoding='utf-8', errors='replace'),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW
)
print(f"Codex PID: {proc.pid}", flush=True)
