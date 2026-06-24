import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"

# matching_v3はcwdをmatching_v3/に変える必要がある
# weekday_guard経由でもcwdを渡せるようにweekday_guard.pyを確認
wg = base / "weekday_guard.py"
print("=== weekday_guard.py cwd処理確認 ===")
wg_text = wg.read_text(encoding="utf-8", errors="replace")
print(wg_text)
