import subprocess, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outreach_system\codex_collect_v2.log"
work_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\outreach_system"

proc = subprocess.Popen(
    'codex exec "SPEC_collect_v2.mdを読んでcollect_targets.pyのFALLBACKドメインを実在企業に差し替えてください。py_compile確認まで。" --dangerously-bypass-approvals-and-sandbox',
    shell=True,
    cwd=work_dir,
    stdout=open(log_path, 'w', encoding='utf-8', errors='replace'),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW
)
print(f"Codex v2 PID: {proc.pid}", flush=True)
