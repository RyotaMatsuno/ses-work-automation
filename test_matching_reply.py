import os
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
os.chdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

# 環境変数をダミーで設定
import os

os.environ.setdefault("LINE_CHANNEL_SECRET", "dummy")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "dummy")
os.environ.setdefault("NOTION_API_KEY", "dummy")
os.environ.setdefault("NOTION_ENGINEER_DB_ID", "dummy")
os.environ.setdefault("NOTION_PROJECT_DB_ID", "dummy")
os.environ.setdefault("ANTHROPIC_API_KEY", "dummy")

from webhook_server import build_matching_result_reply

result = build_matching_result_reply()
print(result)
