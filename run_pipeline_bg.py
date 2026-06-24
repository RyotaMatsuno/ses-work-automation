"""
mail_pipeline 本番実行（PROCESS_LIMIT=20）をバックグラウンド起動
"""

import subprocess
import sys

script = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py"
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log"

# バックグラウンドで起動（タイムアウト回避）
proc = subprocess.Popen(
    [sys.executable, script],
    stdout=open(log, "a", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline",
)
print(f"起動完了 PID={proc.pid}")
print("ログ: pipeline.log に追記中")
