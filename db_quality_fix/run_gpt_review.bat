@echo off
chcp 65001 > nul
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
echo [GPT壁打ち] db_quality_fix 設計レビュー開始...
python db_quality_fix\run_gpt_review.py
echo [完了] output/ フォルダにレビュー結果を保存しました。
pause
