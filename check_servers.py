import sys

sys.stdout.reconfigure(encoding="utf-8")
import requests

# 両方のサーバーでline_queryの粗利ロジックが修正済みか確認
# /healthエンドポイントにversionを含めることはできないが
# 別のエンドポイントで確認できないか

# まずCloud RunとRenderのレスポンスを詳しく確認
for label, url in [
    ("Cloud Run", "https://line-webhook-74735301292.asia-northeast1.run.app"),
    ("Render", "https://ses-work-automation.onrender.com"),
]:
    try:
        r = requests.get(f"{url}/health", timeout=10)
        print(f"[{label}] /health -> {r.status_code}")
        print(f"  body: {r.text[:200]}")
        print(f"  headers: {dict(list(r.headers.items())[:5])}")
    except Exception as e:
        print(f"[{label}] ERROR: {e}")
    print()

# RailwayのURLを特定
# railway.json があるディレクトリのgit remoteを確認
import subprocess

r2 = subprocess.run(
    ["git", "remote", "-v"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("=== git remote ===")
print(r2.stdout)
