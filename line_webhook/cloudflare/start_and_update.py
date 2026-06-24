"""
Quick Tunnelを起動してURLを取得し、
.envのJOBZ_COMMAND_URLを更新してCloud Runを再デプロイする。
スタートアップ登録用にも使用。
"""

import re
import subprocess
import sys
import time

CF = r"C:\Users\ma_py\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"
ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
LOG_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\cloudflare\tunnel.log"
CLOUD_RUN_SERVICE = "line-webhook"
CLOUD_RUN_REGION = "asia-northeast1"


def update_env(key, value):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}\n")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={value}\n")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print(f"[env] {key}={value}", flush=True)


def start_tunnel_and_get_url():
    print("[tunnel] Quick Tunnel起動中...", flush=True)
    with open(LOG_PATH, "w", encoding="utf-8") as log_f:
        proc = subprocess.Popen(
            [CF, "tunnel", "--url", "http://127.0.0.1:8765"], stdout=log_f, stderr=subprocess.STDOUT, text=False
        )
    # ログからURLが出るまで最大30秒待機
    url = None
    for i in range(60):
        time.sleep(0.5)
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            m = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", content)
            if m:
                url = m.group(0)
                break
        except Exception:
            pass
    return url, proc


def redeploy_cloud_run(url):
    print(f"[deploy] Cloud Run再デプロイ: {url}", flush=True)
    cmd = [
        "gcloud",
        "run",
        "services",
        "update",
        CLOUD_RUN_SERVICE,
        "--region",
        CLOUD_RUN_REGION,
        f"--update-env-vars=JOBZ_COMMAND_URL={url}",
        "--quiet",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print(r.stdout[:300], flush=True)
    if r.returncode != 0:
        print(f"[deploy] ERROR: {r.stderr[:300]}", flush=True)
        return False
    return True


if __name__ == "__main__":
    url, proc = start_tunnel_and_get_url()
    if not url:
        print("[ERROR] URLが取得できませんでした。tunnel.logを確認してください。", flush=True)
        sys.exit(1)

    print(f"[OK] Tunnel URL: {url}", flush=True)
    update_env("JOBZ_COMMAND_URL", url)

    ok = redeploy_cloud_run(url)
    if ok:
        print("[完了] Cloud Run再デプロイ成功", flush=True)
    else:
        print("[警告] Cloud Run再デプロイ失敗。手動で更新してください。", flush=True)
        print(f"  JOBZ_COMMAND_URL={url}", flush=True)

    print("\n[待機] トンネル稼働中（Ctrl+Cで停止）", flush=True)
    proc.wait()
