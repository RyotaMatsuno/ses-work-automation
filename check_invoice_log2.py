import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\codex_invoice_sender.log"
with open(log, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
print(content[-2000:] if len(content) > 2000 else content)
