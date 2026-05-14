@echo off
taskkill /IM "Claude.exe" /F 2>nul
timeout /t 3 /nobreak >nul
start "" "C:\Users\ma_py\AppData\Local\AnthropicClaude\claude.exe"
echo Done
