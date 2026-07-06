import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
time.sleep(40)
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\close_senkou.log"
with open(log, 'r', encoding='utf-8') as f:
    print(f.read())
