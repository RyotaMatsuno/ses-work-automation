import subprocess

cmd = [
    r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd",
    "exec",
    "SPEC_drive_fix.mdを読んでTASKS_drive_fix.mdの順番でmail_pipeline.pyのDriveリンクURLフィールドへの書き込みをrich_text型からurl型に修正してください",
    "--dangerously-bypass-approvals-and-sandbox",
]

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\codex_drive_fix.log"

with open(log_path, "w", encoding="utf-8") as log:
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    print(f"PID: {proc.pid}")
    print("Codex起動完了（バックグラウンド実行中）")
