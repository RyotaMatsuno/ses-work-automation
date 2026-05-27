import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CODEX = r'C:\Users\ma_py\AppData\Roaming\npm\codex.cmd'
log_path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_input_label.log'

proc = subprocess.Popen(
    [CODEX, 'exec',
     r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\input_label_spec\SPEC.mdを読んでTASKS.mdの順番で実装してください。input_label_spec/CLAUDE.mdの禁止事項を必ず守ること。',
     '--dangerously-bypass-approvals-and-sandbox',
     '-C', r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work'],
    cwd=r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work',
    stdout=open(log_path, 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW
)
print(f"Codex 入力元ラベル PID: {proc.pid}", flush=True)
