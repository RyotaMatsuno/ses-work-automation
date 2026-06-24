import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"

# wd_matching_v3.bat: matching_v3/に cd してから実行
# %~dp0 で自身のディレクトリを取得 → matching_v3\ サブディレクトリに移動
content_mv3 = f'@echo off\ncd /d "%~dp0matching_v3"\n"{python}" "%~dp0weekday_guard.py" "{python}" "matching_v3.py"\n'
# ASCII確認
assert all(ord(c) < 128 for c in content_mv3), "non-ASCII!"
(base / "wd_matching_v3.bat").write_bytes(content_mv3.encode("ascii"))
print("OK wd_matching_v3.bat")
print(f"content: {repr(content_mv3)}")

# テスト
print("\n=== テスト実行 ===")
r = subprocess.run(
    ["cmd", "/c", str(base / "wd_matching_v3.bat")],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)
print(f"  returncode: {r.returncode}")
out = (r.stdout + r.stderr).strip()
# 先頭200文字だけ表示
for l in out.splitlines()[:20]:
    print(f"  {l}")
