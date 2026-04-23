@echo off
REM ===================================
REM SES自動化 全タスク一括セットアップ
REM このファイルをダブルクリックで実行
REM ===================================

set PYTHON=C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe
set BASE=C:\Users\ma_py\OneDrive\デスクトップ\ses_work

echo ========================================
echo SES自動化 タスクスケジューラ一括登録
echo ========================================
echo.

REM --- Outlook → Notion（1日3回: 9時/13時/18時）---
echo [1/2] Outlook自動取り込み 登録中...
schtasks /create /tn "SES_Outlook_9h"  /tr "\"%PYTHON%\" \"%BASE%\outlook\outlook_to_notion.py\"" /sc daily /st 09:00 /f /rl highest
schtasks /create /tn "SES_Outlook_13h" /tr "\"%PYTHON%\" \"%BASE%\outlook\outlook_to_notion.py\"" /sc daily /st 13:00 /f /rl highest
schtasks /create /tn "SES_Outlook_18h" /tr "\"%PYTHON%\" \"%BASE%\outlook\outlook_to_notion.py\"" /sc daily /st 18:00 /f /rl highest
echo    完了: 毎日9時 / 13時 / 18時 に自動実行
echo.

REM --- Freee 請求書自動生成（毎月25日 10時）---
echo [2/2] Freee請求書自動生成 登録中...
schtasks /create /tn "SES_Freee_Invoice" /tr "\"%PYTHON%\" \"%BASE%\freee\freee_invoice.py\"" /sc monthly /d 25 /st 10:00 /f /rl highest
echo    完了: 毎月25日 AM10時 に自動実行
echo.

echo ========================================
echo 全タスク登録完了！
echo ========================================
echo.
pause
