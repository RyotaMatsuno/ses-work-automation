import subprocess, os

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\sales_pipeline"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_sales_pipeline.log"
codex_cmd = r"C:\Users\ma_py\AppData\Roaming\npm\codex.cmd"

cmd = [
    codex_cmd, "exec",
    "CLAUDE.mdとSPEC.mdを読んでTASKS.mdの順番でT01からT10まで全て実装してください。smoke testまで完走して全タスクにチェックを入れてください。",
    "--dangerously-bypass-approvals-and-sandbox"
]

print(f"Codex起動 PID待ち...", flush=True)
os.makedirs(os.path.dirname(log_path), exist_ok=True)

with open(log_path, "w", encoding="utf-8") as log:
    proc = subprocess.Popen(
        cmd,
        stdout=log,
        stderr=subprocess.STDOUT,
        cwd=cwd
    )
    print(f"PID: {proc.pid}", flush=True)

print("バックグラウンド実行中。logs/codex_sales_pipeline.logで確認。", flush=True)
