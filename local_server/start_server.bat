@echo off
REM jobz-command server launcher (ASCII ONLY - do NOT add Japanese; multibyte chars break cmd parsing)
cd /d "%~dp0"

REM Kill any existing process listening on port 8765
for /f "tokens=5" %%a in ('C:\Windows\System32\netstat.exe -ano ^| findstr ":8765 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Wait a moment, then start the server minimized in the background
C:\Windows\System32\timeout.exe /t 1 /nobreak >nul
start "jobz-command-server" /MIN pythonw command_server.py
echo done
