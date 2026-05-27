
import os
from dotenv import dotenv_values

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
env = dotenv_values(os.path.join(base, "config", ".env"))

# SENDER_NAME等の環境変数確認
keys_to_check = ['SENDER_NAME', 'OUTREACH_SENDER_NAME', 'FP_EMAIL', 'OUTREACH_FROM']
for k in keys_to_check:
    val = env.get(k, 'NOT SET')
    print(f"{k}: {val}")

# outreach.pyのSENDER_NAME読み込み箇所確認
outreach_py = os.path.join(base, "outreach_system", "outreach.py")
with open(outreach_py, encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines[:30]):
    print(f"{i+1}: {line}", end="")
