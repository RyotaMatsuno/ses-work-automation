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
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

# DBスキーマを取得してステータスの選択肢を確認
req = urllib.request.Request(
    f"https://api.notion.com/v1/databases/{PROJECT_DB}",
    headers={
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
    },
    method="GET",
)
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())

status_prop = data.get("properties", {}).get("ステータス", {})
options = status_prop.get("select", {}).get("options", [])
print("ステータス選択肢:")
for o in options:
    print(f"  '{o['name']}'")
