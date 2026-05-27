import subprocess, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\codex_precision.log"
work_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2"

proc = subprocess.Popen(
    'codex exec "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの1〜7番を順番に実装してください。完了したタスクはTASKS.mdを[x]に更新してください。" --dangerously-bypass-approvals-and-sandbox',
    shell=True,
    cwd=work_dir,
    stdout=open(log_path, 'w', encoding='utf-8', errors='replace'),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW
)
print(f"Codex PID: {proc.pid}", flush=True)
print(f"ログ: {log_path}", flush=True)
