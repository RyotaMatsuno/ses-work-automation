import subprocess

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\codex_payment_checker.log"
proc = subprocess.Popen(
    'codex exec "payment_CLAUDE.mdとpayment_SPEC.mdを読んでpayment_TASKS.mdの1〜5番を順番に実装してください" -C freee --dangerously-bypass-approvals-and-sandbox',
    shell=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    stdout=open(log_path, "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
)
print(f"PID: {proc.pid}", flush=True)
