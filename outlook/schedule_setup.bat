@echo off
REM Outlookメール自動チェック タスクスケジューラ登録
REM 毎朝9時に自動実行

set SCRIPT_PATH=C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outlook\outlook_to_notion.py
set PYTHON_PATH=C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe
set TASK_NAME=SES_Outlook_To_Notion

schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" /sc daily /st 09:00 /f /rl highest

echo.
echo タスク登録完了！毎朝9時に自動実行されます。
echo 確認: schtasks /query /tn "%TASK_NAME%"
pause
