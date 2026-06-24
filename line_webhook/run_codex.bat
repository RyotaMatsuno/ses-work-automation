@echo off
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
codex --dangerously-bypass-approvals-and-sandbox -C "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook" "SPEC.mdとCLAUDE.mdを読んでTASKS.mdの順番で実装してください" > codex_skill.log 2>&1
echo EXIT_CODE=%ERRORLEVEL% >> codex_skill.log
