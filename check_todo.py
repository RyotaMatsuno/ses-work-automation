import json
import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

checks = {}

# notify_line 本番送信テスト
result_path = os.path.join(base, "matching_v2", "result.json")
if os.path.exists(result_path):
    with open(result_path, encoding="utf-8") as f:
        data = json.load(f)
    with_cand = [d for d in data if d.get("candidates")]
    checks["result.json更新日時"] = os.path.getmtime(result_path)
    import datetime

    dt = datetime.datetime.fromtimestamp(checks["result.json更新日時"])
    print(f"result.json: {len(data)}件 / candidates有: {len(with_cand)}件 / 更新: {dt}")

# cleanup_v2.py
cleanup = os.path.join(base, "cleanup_v2.py")
print(f"cleanup_v2.py: {'EXISTS' if os.path.exists(cleanup) else 'NOT FOUND'}")

# outreach_system
outreach = os.path.join(base, "outreach_system")
if os.path.exists(outreach):
    files = os.listdir(outreach)
    print(f"outreach_system/: {files}")
else:
    print("outreach_system/: NOT FOUND")

# collect_targets.py
collect = os.path.join(base, "outreach_system", "collect_targets.py")
print(f"collect_targets.py: {'EXISTS' if os.path.exists(collect) else 'NOT FOUND'}")

# freee .env確認
env_path = os.path.join(base, "config", ".env")
from dotenv import dotenv_values

env = dotenv_values(env_path)
print(f"FREEE_ACCESS_TOKEN: {'SET' if env.get('FREEE_ACCESS_TOKEN') else 'EMPTY'}")
print(f"FIRECRAWL_API_KEY: {'SET' if env.get('FIRECRAWL_API_KEY') else 'EMPTY'}")
print(f"GITHUB_PAT: {'SET' if env.get('GITHUB_PAT') else 'EMPTY'}")

# 岡本LINE Webhook
wh = os.path.join(base, "line_webhook", "webhook_server.py")
if os.path.exists(wh):
    with open(wh, encoding="utf-8") as f:
        content = f.read()
    print(f"webhook_server.py: webhook_okamoto {'EXISTS' if 'webhook_okamoto' in content else 'MISSING'}")
