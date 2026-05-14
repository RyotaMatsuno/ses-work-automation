@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [%date% %time%] importer実行開始 >> importer_scheduler.log
python importer.py >> importer_scheduler.log 2>&1
echo [%date% %time%] importer実行完了 >> importer_scheduler.log
