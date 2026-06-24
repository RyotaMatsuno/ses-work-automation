"""
ngrok起動後にURLを取得してRailway環境変数を更新するスクリプト
start_ngrok.batから呼び出される（ngrok起動後5秒後に実行）
"""

import sys
import time

import requests

RAILWAY_TOKEN = "fbc5deef-ab29-4f5c-b7b8-6dc2cc2e9c81"
SERVICE_ID = "484966c3-2d1c-4736-9f69-891f11a35128"
ENVIRONMENT_ID = "46e90371-2c0b-4108-aefa-385df6916300"


def get_ngrok_url(retries=15, wait=2):
    for i in range(retries):
        try:
            res = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
            tunnels = res.json().get("tunnels", [])
            for t in tunnels:
                if t.get("proto") == "https":
                    url = t["public_url"]
                    print(f"[ngrok] URL取得: {url}")
                    return url
        except Exception as e:
            print(f"[ngrok] 待機中... ({i + 1}/{retries}): {e}")
        time.sleep(wait)
    return None


def update_railway_env(ngrok_url):
    query = """
    mutation UpsertVariables($serviceId: String!, $environmentId: String!, $variables: ServiceVariables!) {
        variableCollectionUpsert(input: {
            projectId: "1346ecbb-17a9-4c6f-a6c1-f256c1c5564a",
            serviceId: $serviceId,
            environmentId: $environmentId,
            variables: $variables
        })
    }
    """
    variables = {"serviceId": SERVICE_ID, "environmentId": ENVIRONMENT_ID, "variables": {"NGROK_URL": ngrok_url}}
    res = requests.post(
        "https://backboard.railway.com/graphql/v2",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {RAILWAY_TOKEN}"},
        json={"query": query, "variables": variables},
        timeout=15,
    )
    result = res.json()
    if "errors" in result:
        print(f"[Railway] ERROR: {result['errors']}")
        return False
    print(f"[Railway] NGROK_URL更新完了: {ngrok_url}")
    return True


def redeploy_railway():
    query = """
    mutation Redeploy($serviceId: String!, $environmentId: String!) {
        serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
    }
    """
    res = requests.post(
        "https://backboard.railway.com/graphql/v2",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {RAILWAY_TOKEN}"},
        json={"query": query, "variables": {"serviceId": SERVICE_ID, "environmentId": ENVIRONMENT_ID}},
        timeout=15,
    )
    result = res.json()
    if "errors" in result:
        print(f"[Railway] Redeploy ERROR: {result['errors']}")
        return False
    print("[Railway] 再デプロイ開始")
    return True


if __name__ == "__main__":
    print("ngrok URL取得中...")
    url = get_ngrok_url()
    if not url:
        print("[ERROR] ngrok URLが取得できませんでした")
        sys.exit(1)

    if update_railway_env(url):
        redeploy_railway()
        print(f"\n✅ 完了! Railway NGROK_URL = {url}")
    else:
        print("[ERROR] Railway更新失敗")
        sys.exit(1)
