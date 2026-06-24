import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

IMP = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_attachment_importer"

r = subprocess.run(
    [sys.executable, "importer.py"],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    cwd=IMP,
    env={**os.environ, "DRY_RUN": "1"},
    timeout=60,
)
out = r.stdout
# 文字化け除去して接続結果だけ抜き出す
lines = out.split("\n")
for line in lines:
    # 重要なログだけ表示
    keywords = ["IMAP", "account=", "接続", "INBOX", "未処理", "DRY_RUN", "WARNING", "ERROR", "完了", "スキップ"]
    if any(k in line for k in keywords):
        # 文字化け行は除外
        try:
            line.encode("utf-8")
            print(line)
        except:
            pass
