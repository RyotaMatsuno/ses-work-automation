import subprocess

codex_cmd = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

# ① daily_report.py（ses_work直下）
log1 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_daily_report.log"
with open(log1, "w", encoding="utf-8") as f:
    p1 = subprocess.Popen(
        [
            codex_cmd,
            "exec",
            "SPEC_daily_report.mdを読んで、daily_report.pyを新規作成してください。--dry-runで動作確認できる状態にすること。",
            "--dangerously-bypass-approvals-and-sandbox",
        ],
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print(f"daily_report PID: {p1.pid}", flush=True)

# ② webhook_server.py「進捗」コマンド追加
log2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_webhook_progress.log"
with open(log2, "w", encoding="utf-8") as f:
    p2 = subprocess.Popen(
        [
            codex_cmd,
            "exec",
            r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\SPEC_daily_report.mdを読んで、webhook_server.pyのprocess_message()に「進捗」コマンドを追加してください。他の既存機能は変更しないこと。",
            "--dangerously-bypass-approvals-and-sandbox",
        ],
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
        stdout=f,
        stderr=f,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
    )
    print(f"webhook PID: {p2.pid}", flush=True)
