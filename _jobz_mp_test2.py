import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"

# Pythonバージョン確認
r = subprocess.run([python, "--version"], capture_output=True, text=True, encoding="utf-8", timeout=5)
print(f"■ Pythonバージョン: {r.stdout.strip()}")

# run_pipeline.bat 実行テスト（タイムアウト付き）
print("\n■ run_pipeline.bat 実行テスト（25秒タイムアウト）")
bat = os.path.join(SES, "mail_pipeline", "run_pipeline.bat")
try:
    r2 = subprocess.run(
        bat, shell=True, capture_output=True, text=True, encoding="cp932", errors="replace", cwd=SES, timeout=25
    )
    print(f"  returncode: {r2.returncode}")
    print(f"  stdout: {r2.stdout[:300]}")
    print(f"  stderr: {r2.stderr[:300]}")
except subprocess.TimeoutExpired:
    print("  タイムアウト（25秒）→ 正常起動の可能性大（メール取得で時間がかかる）")

# pipeline.log 末尾15行
print("\n■ pipeline.log 末尾15行")
log = Path(SES) / "mail_pipeline" / "pipeline.log"
with open(log, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
for l in lines[-15:]:
    print("  " + l.rstrip())
