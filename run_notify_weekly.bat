@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "logs" mkdir "logs"
set "LOG_PATH=logs\notify_weekly.log"
echo [%date% %time%] LINE通知開始 >> "%LOG_PATH%"
python matching_v2\notify_line.py >> "%LOG_PATH%" 2>&1
echo [%date% %time%] 完了 >> "%LOG_PATH%"
