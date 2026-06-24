import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outreach_system\codex_collect.log"
work_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outreach_system"

proc = subprocess.Popen(
    'codex exec "CLAUDE_collect.mdとSPEC_collect.mdを読んでTASKS_collect.mdの1〜9番を順番に実装してください。完了したタスクはTASKS_collect.mdを[x]に更新してください。" --dangerously-bypass-approvals-and-sandbox',
    shell=True,
    cwd=work_dir,
    stdout=open(log_path, "w", encoding="utf-8", errors="replace"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW,
)
print(f"Codex PID: {proc.pid}", flush=True)
print(f"ログ: {log_path}", flush=True)
