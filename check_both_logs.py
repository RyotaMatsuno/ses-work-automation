import time, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
time.sleep(90)

logs = {
    "reply_parser": r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\reply_parser\codex_reply_parser.log",
    "invoice_sender": r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\codex_invoice_sender.log",
}
for name, log in logs.items():
    print(f"\n===== {name} =====")
    if os.path.exists(log):
        with open(log, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        print(content[-800:] if len(content) > 800 else content)
    else:
        print("logなし")
