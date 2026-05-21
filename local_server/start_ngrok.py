"""
ngrok起動 → Railway環境変数(NGROK_URL)を自動更新するスクリプト
PC起動時に自動実行される
"""
import subprocess
import time
import requests
import json
import sys
import os

NGROK_EXE = r"C:\Users\ma_py\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"
NGROK_PORT = 8765
RAILWAY_TOKEN = "fbc5deef-ab29-4f5c-b7b8-6dc2cc2e9c81"
SERVICE_ID = "484966c3-2d1c-4736-9f69-891f11a35128"
ENVIRONMENT_ID = "46e90371-2c0b-4108-aefa-385df6916300"

def start_ngrok():
    """ngrokをバックグラウンドで起動"""
    print(f"[ngrok] Starting tunnel on port {NGROK_PORT}...")
    proc = subprocess.Popen(
        [NGROK_EXE, "http", str(NGROK_PORT), "--log=stdout"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return proc

def get_ngrok_url(retries=10, wait=2):
    """ngrok APIからパブリックURLを取得"""
    for i in range(retries):
        try:
            res = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=3)
            tunnels = res.json().get("tunnels", [])
            for t in tunnels:
                if t.get("proto") == "https":
                    url = t["public_url"]
                    print(f"[ngrok] URL: {url}")
                    return url
        except Exception as e:
            print(f"[ngrok] Waiting for tunnel... ({i+1}/{retries})")
        time.sleep(wait)
    return None

def update_railway_env(ngrok_url):
    """Railway環境変数のNGROK_URLを更新"""
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
    variables = {
        "serviceId": SERVICE_ID,
        "environmentId": ENVIRONMENT_ID,
        "variables": {"NGROK_URL": ngrok_url}
    }
    res = requests.post(
        "https://backboard.railway.com/graphql/v2",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RAILWAY_TOKEN}"
        },
        json={"query": query, "variables": variables},
        timeout=15
    )
    result = res.json()
    if "errors" in result:
        print(f"[Railway] ERROR: {result['errors']}")
        return False
    print(f"[Railway] NGROK_URL updated: {ngrok_url}")
    return True

def redeploy_railway():
    """Railway サービスを再デプロイ（環境変数を反映させるため）"""
    query = """
    mutation Redeploy($serviceId: String!, $environmentId: String!) {
        serviceInstanceRedeploy(serviceId: $serviceId, environmentId: $environmentId)
    }
    """
    res = requests.post(
        "https://backboard.railway.com/graphql/v2",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {RAILWAY_TOKEN}"
        },
        json={"query": query, "variables": {"serviceId": SERVICE_ID, "environmentId": ENVIRONMENT_ID}},
        timeout=15
    )
    result = res.json()
    if "errors" in result:
        print(f"[Railway] Redeploy ERROR: {result['errors']}")
        return False
    print("[Railway] Redeploy triggered")
    return True

if __name__ == "__main__":
    # ngrok起動
    proc = start_ngrok()
    
    # URL取得
    url = get_ngrok_url()
    if not url:
        print("[ERROR] ngrok URL取得失敗")
        sys.exit(1)
    
    # Railway環境変数更新
    if update_railway_env(url):
        # 再デプロイ
        redeploy_railway()
        print(f"\n✅ 完了: {url} → Railway NGROK_URL に設定済み")
    else:
        print("[ERROR] Railway環境変数更新失敗")
        sys.exit(1)
    
    print("ngrokトンネルを維持中... (Ctrl+Cで停止)")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("ngrok停止")
