import subprocess, sys
from pathlib import Path

log_path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_pipeline_opt.log'
bat_path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_codex_opt.bat'

with open(log_path, 'w', encoding='utf-8') as lf:
    proc = subprocess.Popen(
        ['cmd.exe', '/c', bat_path],
        stdout=lf,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

print(f"PID: {proc.pid}")
