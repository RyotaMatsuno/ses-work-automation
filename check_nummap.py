# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LQ = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
content = open(LQ, encoding="utf-8").read()

idx = content.find("_NUM_MAP")
print(content[idx : idx + 800])
