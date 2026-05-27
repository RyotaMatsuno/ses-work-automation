import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cmd = [
    r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd",
    "exec",
    "SPEC_v4_diff.mdを読んで記載の差分修正を全て実装してください。既存ファイルは.bak_0526を作成してから修正。完了後にTASKS.mdのPhase8チェックボックスを更新してください。",
    "--dangerously-bypass-approvals-and-sandbox",
    "-C", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"
]

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer\codex_v4.log"
with open(log_path, "w", encoding="utf-8") as logf:
    proc = subprocess.Popen(cmd, stdout=logf, stderr=logf,
                            cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer")

print(f"Codex起動 PID={proc.pid}", flush=True)
print(f"ログ: {log_path}", flush=True)
