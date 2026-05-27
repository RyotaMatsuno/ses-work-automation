@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG_PATH=logs\daily_report.log"
echo [%date% %time%] 日次進捗通知開始 >> "%LOG_PATH%"
python daily_report.py >> "%LOG_PATH%" 2>&1
echo [%date% %time%] 完了 >> "%LOG_PATH%"
