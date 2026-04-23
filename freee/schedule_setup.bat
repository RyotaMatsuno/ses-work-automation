@echo off
REM Freee請求書自動生成 タスクスケジューラ登録
REM 毎月25日 AM10:00 に自動実行

set SCRIPT_PATH=C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\freee_invoice.py
set PYTHON_PATH=C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe
set TASK_NAME=SES_Freee_Invoice

schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc monthly /d 25 /st 10:00 /f /rl highest

echo.
echo ✅ Freeeタスク登録完了！毎月25日AM10時に自動実行されます。
echo 確認: schtasks /query /tn "%TASK_NAME%"
pause
