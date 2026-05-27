@echo off
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
