
import sys, os, subprocess
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SES = os.getcwd()
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"

# -P フラグの有無で import が変わるか確認
print("■ python -P オプション確認")
r = subprocess.run(
    [python, "--help"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
)
if "-P" in r.stdout:
    print("  -P オプション: 存在（sys.path に現在ディレクトリを追加しない）")
else:
    print("  -P オプション: Python 3.11+ 専用。バージョン確認要")

r2 = subprocess.run(
    [python, "--version"],
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5
)
print(f"  Pythonバージョン: {r2.stdout.strip()}")

# mail_pipeline.py を ses_work/ から直接実行テスト（importのみ確認、すぐ終わる）
print("\n■ mail_pipeline.py import テスト（ses_work/ から）")
test_script = """
import sys
sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work')
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mail_pipeline",
        r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py'
    )
    # importだけ試みる（実行はしない）
    print("import spec OK")
except Exception as e:
    print(f"ERROR: {e}")
"""
r3 = subprocess.run(
    [python, "-c", test_script],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    cwd=SES, timeout=15
)
print(f"  stdout: {r3.stdout.strip()}")
print(f"  stderr: {r3.stderr[:300]}")

# run_pipeline.bat を直接実行（タイムアウト付き）
print("\n■ run_pipeline.bat 実行テスト（20秒）")
bat = os.path.join(SES, "mail_pipeline", "run_pipeline.bat")
r4 = subprocess.run(
    bat, shell=True,
    capture_output=True, text=True, encoding="cp932", errors="replace",
    cwd=SES, timeout=25
)
print(f"  returncode: {r4.returncode}")
print(f"  stdout: {r4.stdout[:500]}")
print(f"  stderr: {r4.stderr[:300]}")

# pipeline.log 末尾10行
print("\n■ pipeline.log 末尾10行")
log = Path(SES) / "mail_pipeline" / "pipeline.log"
with open(log, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
for l in lines[-10:]:
    print("  " + l.rstrip())
