import subprocess, os

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\reply_parser\codex_reply_parser.log"
proc = subprocess.Popen(
    'codex exec "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの1〜6番を順番に実装してください" -C reply_parser --dangerously-bypass-approvals-and-sandbox',
    shell=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    stdout=open(log_path, 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT
)
print(f"PID: {proc.pid}", flush=True)
print(f"log: {log_path}", flush=True)
