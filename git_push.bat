@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
git add -A
git commit -m "feat: webhook v4 - okamoto LINE account added (/webhook_okamoto)"
git push origin main
echo.
echo Push complete. Railway will auto-deploy in 2-3 minutes.
pause
