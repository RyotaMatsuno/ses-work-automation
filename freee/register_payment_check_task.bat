@echo off
REM UTF-8
REM freee_payment_check タスクスケジューラ登録
REM 毎月10日・20日・28日 08:00 に freee/payment_checker.py を実行

set TASK_NAME=freee_payment_check
set SCRIPT_PATH=C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\payment_checker.py
set PYTHON_PATH=C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe

schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc monthly /d 10,20,28 /st 08:00 /f /rl highest

echo.
echo freee_payment_check registered. Runs monthly on day 10, 20, and 28 at 08:00.
echo Check: schtasks /query /tn "%TASK_NAME%"
pause
