@echo off
REM UTF-8
REM freee_invoice_send タスクスケジューラ登録
REM 毎月1日 10:00 に freee/invoice_sender.py を実行

set TASK_NAME=freee_invoice_send
set WORK_DIR=C:\Users\ma_py\OneDrive\デスクトップ\ses_work
set SCRIPT_PATH=C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\invoice_sender.py
set PYTHON_PATH=C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe

schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc monthly /d 1 /st 10:00 /f /rl highest

echo.
echo freee_invoice_send registered. Runs monthly on day 1 at 10:00.
echo Check: schtasks /query /tn "%TASK_NAME%"
pause
