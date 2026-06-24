import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

# Cloud Runへのデプロイスクリプトを探す
for root, dirs, files in os.walk(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"):
    for f in files:
        if any(kw in f.lower() for kw in ["deploy", "cloud", "gcloud", "run"]):
            print(os.path.join(root, f))

# gcloud コマンドが使えるか確認
r = subprocess.run(["gcloud", "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print("\n=== gcloud version ===")
print(r.stdout[:200] if r.returncode == 0 else f"NOT FOUND: {r.stderr[:100]}")

# .gcloudignore や cloudbuild.yaml があるか
for fname in [".gcloudignore", "cloudbuild.yaml", "cloudbuild.yml", "deploy.sh", "deploy.bat"]:
    fpath = os.path.join(lw, fname)
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8", errors="replace") as f:
            print(f"\n=== {fname} ===")
            print(f.read()[:300])

# Renderの設定ファイル
for fname in ["render.yaml", "render.yml"]:
    fpath = os.path.join(lw, fname)
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8", errors="replace") as f:
            print(f"\n=== {fname} ===")
            print(f.read()[:300])
