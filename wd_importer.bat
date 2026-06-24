@echo off
cd /d "%~dp0"
"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe" "%~dp0weekday_guard.py" cmd /c "%~dp0mail_attachment_importer\run_importer.bat"
