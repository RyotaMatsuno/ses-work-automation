import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

GCLOUD = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# まずdrive_uploader.pyをline_webhookディレクトリにコピー（Cloud Runから使えるように）
import shutil

src = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\drive_uploader.py"
dst = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\drive_uploader.py"
shutil.copy2(src, dst)
print("drive_uploader.py → line_webhook/ にコピー完了", flush=True)

# requirements.txtにgoogle-authが入っているか確認・追記
req_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\requirements.txt"
with open(req_path, encoding="utf-8") as f:
    req_content = f.read()

additions = []
if "google-auth" not in req_content:
    additions.append("google-auth")
if "google-api-python-client" not in req_content:
    additions.append("google-api-python-client")

if additions:
    with open(req_path, "a", encoding="utf-8") as f:
        for a in additions:
            f.write(f"\n{a}")
    print(f"requirements.txtに追記: {additions}", flush=True)
else:
    print("requirements.txt: google-auth系ライブラリ確認済み", flush=True)

# config/drive_token.jsonもline_webhook/configにコピー
os.makedirs(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\config", exist_ok=True)
src2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\drive_token.json"
dst2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\config\drive_token.json"
shutil.copy2(src2, dst2)
print("drive_token.json → line_webhook/config/ にコピー完了", flush=True)
print("デプロイ準備完了", flush=True)
