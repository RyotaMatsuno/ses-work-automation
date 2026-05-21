@echo off
set NGROK="C:\Users\ma_py\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
start "ngrok" %NGROK% http 8765
timeout /t 5 /nobreak > nul
python "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\update_railway_ngrok.py"
