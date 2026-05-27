@echo off
chcp 65001 >nul
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline"

echo [%date% %time%] ===== mail_pipeline 開始 ===== >> pipeline.log 2>&1
python mail_pipeline.py >> pipeline.log 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] mail_pipeline 失敗 >> pipeline.log 2>&1
    exit /b 1
)
echo [%date% %time%] mail_pipeline 完了 >> pipeline.log 2>&1

echo [%date% %time%] ===== matching_v2 開始 ===== >> pipeline.log 2>&1
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
python matching_v2\matching_v2.py >> mail_pipeline\pipeline.log 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] matching_v2 失敗（続行） >> mail_pipeline\pipeline.log 2>&1
) else (
    echo [%date% %time%] matching_v2 完了 >> mail_pipeline\pipeline.log 2>&1
    echo [%date% %time%] ===== notify_line 開始 ===== >> mail_pipeline\pipeline.log 2>&1
    python matching_v2\notify_line.py >> mail_pipeline\pipeline.log 2>&1
    echo [%date% %time%] notify_line 完了 >> mail_pipeline\pipeline.log 2>&1
)

echo [%date% %time%] ===== 全処理完了 ===== >> mail_pipeline\pipeline.log 2>&1
