@echo off
cd /d "%~dp0"
python "%~dp0cost_control\project_expiry.py" >> "%~dp0cost_control\project_expiry_task.log" 2>&1
