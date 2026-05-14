@echo off
cd /d "C:\Users\ma_py\OneDrive\Desktop\ses_work\local_server"
if exist "%~dp0..\..\..\..\Desktop\ses_work\local_server\command_server.py" (
    cd /d "%~dp0..\..\..\..\Desktop\ses_work\local_server"
)
start "jobz-command-server" /MIN pythonw command_server.py
