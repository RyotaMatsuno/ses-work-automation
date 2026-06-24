import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

# git log で push済みコミットを確認
r = subprocess.run(
    ["git", "log", "--oneline", "-8"], cwd=lw, capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("=== git log ===")
print(r.stdout)

# Railwayの実際のデプロイ先URLを確認
# railway.json / .env / webhook_server.py のLINE_WEBHOOK_URL等を確認
for fname in [".env", "railway.json"]:
    fpath = os.path.join(lw, fname)
    if os.path.exists(fpath):
        with open(fpath, encoding="utf-8", errors="replace") as f:
            print(f"\n=== {fname} ===")
            print(f.read()[:500])

# webhook_server.py のLINE webhook URLハードコードを確認
wh_path = os.path.join(lw, "webhook_server.py")
with open(wh_path, encoding="utf-8") as f:
    lines = f.readlines()

print("\n=== webhook_server.py: URL/Railway/render関連 ===")
for i, line in enumerate(lines, 1):
    if any(kw in line.lower() for kw in ["railway", "render", "onrender", "run.app", "url", "host"]):
        if "import" not in line and "#" not in line[:3]:
            print(f"L{i}: {line.rstrip()[:120]}")
