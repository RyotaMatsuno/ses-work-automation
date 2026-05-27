import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
r = subprocess.run(
    ['python', 'wall_hitting.py', '--problem', 'テスト疎通確認'],
    capture_output=True,
    cwd=r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work',
    timeout=90
)
out = r.stdout.decode('utf-8', errors='replace')
print(out[:2000])
if r.returncode != 0:
    print('STDERR:', r.stderr.decode('utf-8', errors='replace')[:300])
print('RC:', r.returncode)
