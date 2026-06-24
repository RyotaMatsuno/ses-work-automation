import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"

# %~dp0 を使えばbat自身のディレクトリを日本語パスなしで参照できる
# weekday_guard.pyもbat自身と同じディレクトリにあるので %~dp0weekday_guard.py で解決

bat_defs = {
    "wd_mail_pipeline.bat": (f'"{python}" "%~dp0weekday_guard.py" cmd /c "%~dp0mail_pipeline\\run_pipeline.bat"'),
    "wd_matching_v3.bat": (f'"{python}" "%~dp0weekday_guard.py" "{python}" "%~dp0matching_v3\\matching_v3.py"'),
    "wd_cost_guard.bat": (f'"{python}" "%~dp0weekday_guard.py" "{python}" "%~dp0cost_guard.py"'),
    "wd_importer.bat": (f'"{python}" "%~dp0weekday_guard.py" cmd /c "%~dp0mail_attachment_importer\\run_importer.bat"'),
    "wd_outlook.bat": (f'"{python}" "%~dp0weekday_guard.py" "{python}" "%~dp0outlook\\outlook_to_notion.py"'),
    "wd_daily_report.bat": (f'"{python}" "%~dp0weekday_guard.py" cmd /c "%~dp0run_daily_report.bat"'),
}

print("=== wd_*.bat 再生成（%~dp0方式） ===")
for bat_name, cmd in bat_defs.items():
    bat_path = base / bat_name
    # %~dp0 と python のフルパスはASCIIのみ
    content = f'@echo off\ncd /d "%~dp0"\n{cmd}\n'
    # ASCII確認
    non_ascii = [(i, c) for i, c in enumerate(content) if ord(c) >= 128]
    if non_ascii:
        print(f"  NG {bat_name}: 非ASCII {non_ascii[:3]}")
        continue
    bat_path.write_bytes(content.encode("ascii"))
    print(f"  OK {bat_name} ({len(content)} bytes)")

# wd_matching_v3.bat の内容確認
print("\n=== wd_matching_v3.bat 確認 ===")
bat = base / "wd_matching_v3.bat"
print(repr(bat.read_bytes().decode("ascii")))

# テスト実行（dry-run）
print("\n=== wd_matching_v3.bat テスト実行 ===")
r = subprocess.run(
    ["cmd", "/c", str(bat)],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(base),
    timeout=30,
)
print(f"  returncode: {r.returncode}")
print(f"  stdout: {r.stdout.strip()[:200]}")
print(f"  stderr: {r.stderr.strip()[:200]}")
