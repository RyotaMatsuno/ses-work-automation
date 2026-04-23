@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
git add -A
git commit -m "feat: AI matching v3, double check separated, okamoto claude code guide"
git push origin main
echo.
echo Push complete. Railway will auto-deploy in 2-3 minutes.
pause
