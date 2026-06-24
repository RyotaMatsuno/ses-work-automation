import requests

TUNNEL_URL = "https://sessions-bone-immune-mtv.trycloudflare.com"
AUTH_TOKEN = "jobz-terra-2026"

# jobz-commandのhealthチェック（トンネル経由）
try:
    r = requests.get(f"{TUNNEL_URL}/health", headers={"X-Auth-Token": AUTH_TOKEN}, timeout=15)
    print(f"status: {r.status_code}")
    print(f"body: {r.text[:200]}")
except Exception as e:
    print(f"ERROR: {e}")
