@echo off
chcp 65001 >nul
REM ===================================
REM SES自動化 全タスク一括セットアップ
REM ===================================

set PYTHON=py
set BASE=C:\Users\ma_py\OneDrive\デスクトップ\ses_work

echo ========================================
echo SES Task Scheduler Setup
echo ========================================
echo.

echo [1/2] Outlook...
schtasks /create /tn "SES_Outlook_9h"  /tr "py \"%BASE%\outlook\outlook_to_notion.py\"" /sc daily /st 09:00 /f /rl highest
schtasks /create /tn "SES_Outlook_13h" /tr "py \"%BASE%\outlook\outlook_to_notion.py\"" /sc daily /st 13:00 /f /rl highest
schtasks /create /tn "SES_Outlook_18h" /tr "py \"%BASE%\outlook\outlook_to_notion.py\"" /sc daily /st 18:00 /f /rl highest
echo    Done: 9h / 13h / 18h
echo.

echo [2/2] Freee...
schtasks /create /tn "SES_Freee_Invoice" /tr "py \"%BASE%\freee\freee_invoice.py\"" /sc monthly /d 25 /st 10:00 /f /rl highest
echo    Done: Monthly 25th 10:00
echo.

echo ========================================
echo All tasks registered!
echo ========================================
echo.
pause
