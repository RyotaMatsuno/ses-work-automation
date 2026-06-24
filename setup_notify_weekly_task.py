import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

bat_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_notify_weekly.bat"

# ① 毎日実行のrun_matching_and_notify.batからnotify部分を削除（matchingのみに変更）
# run_matching_and_notify.batを上書き
new_bat = r"""@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG_PATH=logs\matching_daily.log"
echo [%date% %time%] マッチング開始 >> "%LOG_PATH%"
python matching_v2\matching_v2.py >> "%LOG_PATH%" 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] マッチング完了 >> "%LOG_PATH%"
) else (
    echo [%date% %time%] マッチング失敗 >> "%LOG_PATH%"
)
echo [%date% %time%] 完了 >> "%LOG_PATH%"
"""
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_matching_and_notify.bat", "w", encoding="utf-8") as f:
    f.write(new_bat)
print("run_matching_and_notify.bat: notify削除OK")

# ② notify週2回タスク登録（月・木 9:00）
r = subprocess.run(
    [
        "schtasks",
        "/create",
        "/tn",
        "jobz_notify_weekly",
        "/tr",
        bat_path,
        "/sc",
        "WEEKLY",
        "/d",
        "MON,THU",
        "/st",
        "09:00",
        "/f",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(f"タスク登録: {r.stdout.strip() or r.stderr.strip()}")
print(f"returncode: {r.returncode}")
