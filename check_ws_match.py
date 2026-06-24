# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py"
content = open(WS, encoding="utf-8").read()

# webhook_server.pyのrun_reverse_matchingを確認
idx = content.find("def run_reverse_matching(engineer, projects):")
print(content[idx : idx + 800])
