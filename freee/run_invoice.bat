@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee"
echo [%date% %time%] freee請求書自動生成 開始 >> invoice_auto.log
python freee_invoice_v2.py >> invoice_auto.log 2>&1
echo [%date% %time%] 完了 >> invoice_auto.log
