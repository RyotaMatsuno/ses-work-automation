import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

r = subprocess.run(
    ['python', 'wall_hitting.py', '--problem', 'Pythonでrequests.getが毎回タイムアウトする。同じURLをブラウザで開くと正常に表示される。', '--search'],
    capture_output=True, cwd=r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work', timeout=60
)
print(r.stdout.decode('utf-8', errors='replace'))
print('RC:', r.returncode)
