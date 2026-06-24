import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

# git log確認
r = subprocess.run(
    ["git", "log", "--oneline", "-5"], cwd=lw, capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("=== git log ===")
print(r.stdout)
print(r.stderr[:200] if r.stderr else "")

# Cloud Run URL確認
import os

env_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
from dotenv import dotenv_values

env = dotenv_values(env_path)
cr_url = env.get("CLOUD_RUN_URL") or env.get("WEBHOOK_URL") or env.get("LINE_WEBHOOK_URL") or ""
print(f"\nCloud Run URL: {cr_url!r}")

# .envの全キーを確認（URL系）
for k, v in env.items():
    if "url" in k.lower() or "run" in k.lower() or "railway" in k.lower() or "render" in k.lower():
        print(f"  {k}={v!r}")

# Railwayの設定ファイルがあるか確認
for fname in ["railway.json", "railway.toml", ".railway", "Procfile"]:
    fpath = os.path.join(lw, fname)
    if os.path.exists(fpath):
        print(f"\n[{fname}]")
        with open(fpath, encoding="utf-8", errors="replace") as f:
            print(f.read())
