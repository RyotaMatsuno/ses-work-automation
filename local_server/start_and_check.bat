@echo off
echo [jobz-command] Starting server...
echo Script location: %~dp0
cd /d "%~dp0"
echo Current dir: %CD%
start "jobz-command-server" /MIN pythonw command_server.py
echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul
echo Health check:
curl -s http://127.0.0.1:8765/health
echo.
echo If you see {"status":"ok"} above, server is running.
pause
