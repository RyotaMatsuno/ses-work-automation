bat_content = """@echo off
cd /d "C:\\Users\\ma_py\\OneDrive\\Desktop\\ses_work"
"C:\\Users\\ma_py\\AppData\\Roaming\\npm\\codex.cmd" --dangerously-bypass-approvals-and-sandbox -C "C:\\Users\\ma_py\\OneDrive\\Desktop\\ses_work" "Read PFIX_SPEC.md and PFIX_TASKS.md, then implement all tasks. Target source files: mail_pipeline/mail_pipeline.py, matching_v2/matching_v2.py, matching_v2/notify_line.py. Mark each TASKS item done as you finish it." > codex_pipeline_fix3.log 2>&1
echo exit=%errorlevel% >> codex_pipeline_fix3.log
"""

# OneDriveのDesktopパスを使う
import os
# 実際のパスを確認
desktop = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'
bat_path = os.path.join(desktop, 'run_codex_fix3.bat')

# batファイルは英語のみ（文字化け防止）
bat_en = """@echo off
set CDPATH=
"C:\\Users\\ma_py\\AppData\\Roaming\\npm\\codex.cmd" --dangerously-bypass-approvals-and-sandbox -C "C:\\Users\\ma_py\\OneDrive\\Desktop\\ses_work" "Read PFIX_SPEC.md and PFIX_TASKS.md and implement all tasks listed. Files to modify: mail_pipeline/mail_pipeline.py, matching_v2/matching_v2.py, matching_v2/notify_line.py" > "C:\\Users\\ma_py\\OneDrive\\Desktop\\ses_work\\codex_pfix.log" 2>&1
"""

with open(bat_path, 'w', encoding='ascii') as f:
    f.write(bat_en)
print(f'bat written: {bat_path}')
