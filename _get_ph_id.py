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
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# P.H さんのページIDを取得
payload = {"filter": {"property": "最寄り駅", "rich_text": {"contains": "京成小岩"}}}
body = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
    data=body,
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    },
    method="POST",
)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())

results = data.get("results", [])
if not results:
    print("エンジニアが見つかりません")
    sys.exit(1)

page = results[0]
page_id = page["id"]
current_rate = page["properties"].get("単価（万円）", {}).get("number", "")
name = page["properties"]["名前"]["title"][0]["plain_text"]
print(f"対象: {name} (ID={page_id})")
print(f"現在の単価: {current_rate}万円")
