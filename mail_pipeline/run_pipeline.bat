@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo [%date% %time%] ===== mail_pipeline START ===== >> mail_pipeline\pipeline.log 2>&1
python -P mail_pipeline\mail_pipeline.py >> mail_pipeline\pipeline.log 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] mail_pipeline FAIL >> mail_pipeline\pipeline.log 2>&1
    exit /b 1
)
echo [%date% %time%] mail_pipeline DONE >> mail_pipeline\pipeline.log 2>&1

REM ===== matching_v2 / notify_line disabled by Jobz 2026-06-17 =====
REM Reason: matching_v2/skill_judge.py JSONDecodeError (max_tokens=8000 cutoff)
REM         every hour failure + ~$0.04 per call cost waste
REM Restore: rename run_pipeline.bat.bak_before_matching_v2_remove_20260617_195211 back
REM Wall-hitting: auto_coder/wall_hitting_bugs_round1.txt
REM ================================================================

echo [%date% %time%] ===== ALL DONE (matching_v2 skipped) ===== >> mail_pipeline\pipeline.log 2>&1
