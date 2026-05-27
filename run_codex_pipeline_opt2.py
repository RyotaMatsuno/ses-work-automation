import subprocess, sys
from pathlib import Path

log_path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_pipeline_opt.log'
codex_cmd = r'C:\Users\ma_py\AppData\Roaming\npm\codex.cmd'
work_dir = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline'
prompt = "SPEC_opt.mdとCLAUDE_opt.mdを読んでTASKS_opt.mdの順番でmail_pipeline.pyを改修してください。"

with open(log_path, 'w', encoding='utf-8') as lf:
    proc = subprocess.Popen(
        [codex_cmd, '--dangerously-bypass-approvals-and-sandbox', '-C', work_dir, prompt],
        stdout=lf,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdin=subprocess.DEVNULL
    )

print(f"Codex PID: {proc.pid}")
print("起動完了")
