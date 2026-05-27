@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Codex starting...
codex exec "attachment_importer/CLAUDE.mdとattachment_importer/SPEC.mdとattachment_importer/TASKS.mdを読んでTASKS.mdの順番でPhase1からPhase6まで実装してください" --dangerously-bypass-approvals-and-sandbox > attachment_importer\codex.log 2>&1
echo Codex done, exit code: %ERRORLEVEL%
