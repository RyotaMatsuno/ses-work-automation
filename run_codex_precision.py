import subprocess, os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\codex_precision.log"
proc = subprocess.Popen(
    'codex exec "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの1〜7番を順番に実装してください" -C matching_v2 --dangerously-bypass-approvals-and-sandbox',
    shell=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    stdout=open(log_path, 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT
)
print(f"PID: {proc.pid}", flush=True)
print(f"log: {log_path}", flush=True)
