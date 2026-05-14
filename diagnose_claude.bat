@echo off
chcp 65001 >nul
echo ===== Claude Config Diagnosis ===== > "%~dp0diagnosis.txt"
echo. >> "%~dp0diagnosis.txt"

echo --- APPDATA\Claude\ --- >> "%~dp0diagnosis.txt"
if exist "%APPDATA%\Claude\claude_desktop_config.json" (
    echo EXISTS >> "%~dp0diagnosis.txt"
) else (
    echo NOT FOUND >> "%~dp0diagnosis.txt"
)

echo. >> "%~dp0diagnosis.txt"
echo --- Store Version Path --- >> "%~dp0diagnosis.txt"
if exist "%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json" (
    echo EXISTS >> "%~dp0diagnosis.txt"
    type "%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json" >> "%~dp0diagnosis.txt"
) else (
    echo NOT FOUND >> "%~dp0diagnosis.txt"
)

echo. >> "%~dp0diagnosis.txt"
echo --- AnthropicClaude Path --- >> "%~dp0diagnosis.txt"
if exist "%LOCALAPPDATA%\AnthropicClaude\claude_desktop_config.json" (
    echo EXISTS >> "%~dp0diagnosis.txt"
    type "%LOCALAPPDATA%\AnthropicClaude\claude_desktop_config.json" >> "%~dp0diagnosis.txt"
) else (
    echo NOT FOUND >> "%~dp0diagnosis.txt"
)

echo. >> "%~dp0diagnosis.txt"
echo --- Searching all Claude configs --- >> "%~dp0diagnosis.txt"
where /r "%LOCALAPPDATA%" claude_desktop_config.json 2>nul >> "%~dp0diagnosis.txt"
where /r "%APPDATA%" claude_desktop_config.json 2>nul >> "%~dp0diagnosis.txt"

echo Done.
timeout /t 3 /nobreak >nul
