import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
r = subprocess.run(
    ['python', r'outreach_system\outreach.py', '--dry-run'],
    capture_output=True,
    cwd=r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work',
    timeout=30
)
print(r.stdout.decode('utf-8', errors='replace')[:2000])
print('STDERR:', r.stderr.decode('utf-8', errors='replace')[:500])
print('RC:', r.returncode)
