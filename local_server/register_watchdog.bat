@echo off
echo [jobz-watchdog] Registering task...
schtasks /create /tn "jobz-watchdog" /xml "%~dp0jobz_watchdog_task.xml" /f
if %ERRORLEVEL% == 0 (
    echo [OK] Task registered successfully.
    echo jobz-command will auto-start on login and check every 5 minutes.
) else (
    echo [FAIL] Registration failed. Try running as Administrator.
)
pause
