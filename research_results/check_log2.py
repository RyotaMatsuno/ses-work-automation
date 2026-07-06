import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
time.sleep(30)

log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\close_senkou.log"
with open(log, 'r', encoding='utf-8') as f:
    content = f.read()
if content:
    print(content)
else:
    print("Log still empty. Checking process...")
    import subprocess
    result = subprocess.run(["tasklist", "/FI", "PID eq 33516"], capture_output=True, text=True)
    print(result.stdout)
