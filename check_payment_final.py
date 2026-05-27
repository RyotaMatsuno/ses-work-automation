import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\codex_payment_checker.log"
with open(log, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
if '完了報告' in content:
    idx = content.index('完了報告')
    print(content[idx:idx+1200])
else:
    print(content[-1000:])
