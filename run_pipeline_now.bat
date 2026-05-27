@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
python -m mail_pipeline.mail_pipeline >> mail_pipeline\pipeline.log 2>&1
echo exit_code=%errorlevel% >> mail_pipeline\pipeline.log
