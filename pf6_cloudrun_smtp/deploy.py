import sys

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

# 必要な3つのパスワードを取得
matsuno_pw = config.get("MATSUNO_PASSWORD", "")
okamoto_pw = config.get("OKAMOTO_PASSWORD", "")
sessales_pw = config.get("SESSALES_MAIL_PASSWORD", "") or config.get("SESSALES_PASSWORD", "")

# 存在確認（値は出力しない）
print(f"MATSUNO_PASSWORD: {'OK' if matsuno_pw else 'NG(空)'}")
print(f"OKAMOTO_PASSWORD: {'OK' if okamoto_pw else 'NG(空)'}")
print(f"SESSALES_MAIL_PASSWORD: {'OK' if sessales_pw else 'NG(空)'}")

# gcloudで環境変数を追加 + 再デプロイ
import subprocess

gcloud = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
line_webhook_dir = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pf6_cloudrun_smtp\deploy.log"

env_str = f"MATSUNO_MAIL_PASSWORD={matsuno_pw},OKAMOTO_MAIL_PASSWORD={okamoto_pw},SESSALES_MAIL_PASSWORD={sessales_pw}"

cmd = [
    gcloud,
    "run",
    "deploy",
    "line-webhook",
    "--source",
    ".",
    "--region",
    "asia-northeast1",
    "--max-instances=1",
    "--timeout=60",
    "--allow-unauthenticated",
    "--update-env-vars",
    env_str,
]

print("\nデプロイ開始（パスワード3件追加 + ソース再ビルド）", flush=True)
with open(log_path, "w", encoding="utf-8") as lf:
    proc = subprocess.Popen(cmd, stdout=lf, stderr=lf, cwd=line_webhook_dir, creationflags=subprocess.CREATE_NO_WINDOW)
print(f"deploy PID={proc.pid}")
print(f"log: {log_path}")
