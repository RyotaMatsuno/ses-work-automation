import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
# 変更されたファイルのサイズを確認
files = {
    "drive_uploader.py": "",
    "config/send_counter.json": "",
    "mail_pipeline/mail_pipeline.py": "",
    "matching_v2/notify_line.py": "",
    "line_webhook/webhook_server.py": "",
}
print("=== 実装済みファイル確認 ===", flush=True)
for f in files:
    full = os.path.join(BASE, f)
    if os.path.exists(full):
        sz = os.path.getsize(full)
        mtime = os.path.getmtime(full)
        import datetime

        dt = datetime.datetime.fromtimestamp(mtime).strftime("%m/%d %H:%M")
        print(f"  {f}: {sz}bytes ({dt})", flush=True)
    else:
        print(f"  {f}: 未作成", flush=True)

# webhook_server.pyがCloud Runに含まれているか確認
print("", flush=True)
print("=== Cloud Run対象ファイル確認 ===", flush=True)
cloudrun_files = [
    "line_webhook/Dockerfile",
    "line_webhook/requirements.txt",
]
for f in cloudrun_files:
    full = os.path.join(BASE, f)
    print(f"  {f}: {'OK' if os.path.exists(full) else 'なし'}", flush=True)
