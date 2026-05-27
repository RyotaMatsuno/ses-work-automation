import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')

bat_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_daily_report.bat"

# バットファイル作成
with open(bat_path, "w", encoding="utf-8") as f:
    f.write("""@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG_PATH=logs\\daily_report.log"
echo [%date% %time%] 日次進捗通知開始 >> "%LOG_PATH%"
python daily_report.py >> "%LOG_PATH%" 2>&1
echo [%date% %time%] 完了 >> "%LOG_PATH%"
""")

# タスクスケジューラ登録（毎日8時）
r = subprocess.run([
    "schtasks", "/create",
    "/tn", "jobz_daily_report",
    "/tr", bat_path,
    "/sc", "DAILY",
    "/st", "08:00",
    "/f"
], capture_output=True, text=True, encoding="utf-8", errors="replace")
print(f"タスク登録: returncode={r.returncode}")
print(r.stdout.strip() or r.stderr.strip())

# dry-runで最終確認
r2 = subprocess.run(
    ["python", "daily_report.py", "--dry-run"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30
)
print(f"\n--- dry-run ---")
print(r2.stdout[:400])
