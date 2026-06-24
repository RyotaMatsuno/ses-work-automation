import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

checks = {
    "LINE_CHANNEL_ACCESS_TOKEN": "松野公式LINEトークン",
    "MATSUNO_LINE_USER_ID": "松野USER_ID",
    "OKAMOTO_LINE_CHANNEL_ACCESS_TOKEN": "岡本公式LINEトークン",
    "OKAMOTO_LINE_USER_ID": "岡本USER_ID",
}
for key, label in checks.items():
    val = os.environ.get(key, "")
    status = "OK" if val else "NG（未設定）"
    preview = val[:8] + "..." if val else "-"
    print(f"{label} ({key}): {status} [{preview}]")
