import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 1. drive_uploader単体テスト（実際にアップロード）
print("=== TEST1: drive_uploader.py ===", flush=True)
r = subprocess.run(
    ["python", "drive_uploader.py"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=BASE
)
print("stdout:", r.stdout[:500], flush=True)
print("stderr:", r.stderr[:300], flush=True)
print("returncode:", r.returncode, flush=True)

# 2. send_counter.json確認
print("\n=== TEST2: send_counter.json ===", flush=True)
import json

with open(os.path.join(BASE, "config/send_counter.json"), encoding="utf-8") as f:
    sc = json.load(f)
print(json.dumps(sc, ensure_ascii=False), flush=True)

# 3. mail_pipeline DRY_RUN
print("\n=== TEST3: mail_pipeline DRY_RUN（構文チェック） ===", flush=True)
r2 = subprocess.run(
    ["python", "-c", 'import mail_pipeline.mail_pipeline; print("import OK")'],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=BASE,
    env={**os.environ, "DRY_RUN": "1"},
)
print("stdout:", r2.stdout[:300], flush=True)
print("stderr:", r2.stderr[:500], flush=True)
