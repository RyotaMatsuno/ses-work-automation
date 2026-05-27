import subprocess, sys

codex = r'C:\Users\ma_py\AppData\Roaming\npm\codex.cmd'
ses_work = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'
log_path = ses_work + r'\codex_pipeline_fix2.log'

instruction = "Read PFIX_SPEC.md and PFIX_TASKS.md, then implement all tasks. Target source files: mail_pipeline/mail_pipeline.py, matching_v2/matching_v2.py, matching_v2/notify_line.py. Mark each TASKS.md item done as you finish it."

proc = subprocess.Popen(
    [codex, '--dangerously-bypass-approvals-and-sandbox', '-C', ses_work, instruction],
    stdout=open(log_path, 'w', encoding='utf-8', buffering=1),
    stderr=subprocess.STDOUT,
    creationflags=0x00000008
)
print(f'Codex PID: {proc.pid}')
print(f'Log: codex_pipeline_fix2.log')
