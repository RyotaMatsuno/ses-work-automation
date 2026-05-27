import sys, os, subprocess
sys.stdout.reconfigure(encoding='utf-8')

checks = []

# 1. cleanup_v2.py未実行確認
r = subprocess.run(["python", "-c", """
import requests
from dotenv import dotenv_values
config = dotenv_values(r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work\\config\\.env')
h = {"Authorization": f"Bearer {config['NOTION_API_KEY']}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
r = requests.post("https://api.notion.com/v1/databases/343450ff-37c0-819d-8769-fb0a8a4ceeb1/query",
    headers=h, json={"page_size": 1})
print(r.json().get('next_cursor','') or 'cursor:None')
# 件数確認用
r2 = requests.post("https://api.notion.com/v1/databases/343450ff-37c0-819d-8769-fb0a8a4ceeb1/query",
    headers=h, json={"page_size": 100})
d = r2.json()
cnt = len(d.get('results', []))
has_more = d.get('has_more', False)
print(f"エンジニアDB: {cnt}件以上" if has_more else f"エンジニアDB: {cnt}件")
"""], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
print("=== エンジニアDB件数 ===")
print(r.stdout.strip() or r.stderr[:200])

# 2. notify_line.py テスト状況
notify_log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\notify_line_run.log"
if os.path.exists(notify_log):
    size = os.path.getsize(notify_log)
    print(f"\n=== notify_line.log ({size}bytes) ===")
    with open(notify_log, encoding="utf-8", errors="replace") as f:
        print(f.read()[-300:])
else:
    print("\nnotify_line.log: なし")

# 3. 岡本LINE Webhook状況
print("\n=== 岡本LINE Webhook ===")
print("設定URL: https://line-webhook-74735301292.asia-northeast1.run.app/webhook_okamoto")
print("状態: 岡本からアクセス許可待ち（変化なし）")
