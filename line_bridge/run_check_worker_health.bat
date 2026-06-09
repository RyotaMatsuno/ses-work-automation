@echo off
chcp 65001 >nul
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
python line_bridge\check_worker_health.py >> line_bridge\worker_health.log 2>&1
