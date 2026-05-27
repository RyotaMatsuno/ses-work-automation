import subprocess, sys

proc = subprocess.Popen(
    [sys.executable, '-m', 'matching_v2.matching_v2'],
    cwd=r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work',
    stdout=open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_run_test.log', 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT,
    creationflags=0x00000008
)
print(f'PID: {proc.pid}')
