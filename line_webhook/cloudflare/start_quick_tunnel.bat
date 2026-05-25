@echo off
chcp 65001 > nul
set CF=C:\Users\ma_py\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe
set LOG=C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\cloudflare\tunnel.log

echo Starting Quick Tunnel...
%CF% tunnel --url http://127.0.0.1:8765 > "%LOG%" 2>&1
