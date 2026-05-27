import subprocess
proc = subprocess.Popen(
    ['python', 'matching_v2/notify_line.py'],
    cwd=r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work',
    stdout=open('notify_line_test.log', 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT
)
print(f"PID: {proc.pid}", flush=True)
