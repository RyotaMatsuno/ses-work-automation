@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server"

REM 既存の8765ポートプロセスを全てkill
for /f "tokens=5" %%a in ('C:\Windows\System32\netstat.exe -ano ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM 少し待ってから起動
C:\Windows\System32\timeout.exe /t 1 /nobreak >nul
start "jobz-command-server" /MIN pythonw command_server.py
echo done
