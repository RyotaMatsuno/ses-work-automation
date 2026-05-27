import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import dotenv_values
config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

print(f"LINE_CHANNEL_SECRET: {config.get('LINE_CHANNEL_SECRET','NOT SET')}")
print(f"MATSUNO_LINE_USER_ID: {config.get('MATSUNO_LINE_USER_ID','NOT SET')}")
print(f"LINE_CHANNEL_ACCESS_TOKEN (先頭20): {config.get('LINE_CHANNEL_ACCESS_TOKEN','NOT SET')[:20]}")
