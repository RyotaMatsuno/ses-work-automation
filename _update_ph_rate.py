import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_env():
    env = {}
    with open("config/.env", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


env = load_env()
token = env.get("NOTION_API_KEY", "")

page_id = "37c450ff-37c0-81ed-afa7-cbf210c027af"

payload = {"properties": {"単価（万円）": {"number": 32}}}
body = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    f"https://api.notion.com/v1/pages/{page_id}",
    data=body,
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    },
    method="PATCH",
)
with urllib.request.urlopen(req, timeout=15) as resp:
    result = json.loads(resp.read())

updated = result["properties"]["単価（万円）"]["number"]
print(f"✅ 単価更新完了: 40万 → {updated}万円")
