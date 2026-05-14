
import subprocess, sys, os
os.chdir(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work')
log = open('cleanup_v2.log', 'w', encoding='utf-8')
proc = subprocess.Popen([sys.executable, '-u', 'cleanup_v2.py'], stdout=log, stderr=log)
print(f"PID={proc.pid}")
