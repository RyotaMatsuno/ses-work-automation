import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# Gmailなどで使われているGoogle認証情報を探す
search_dirs = [
    r"C:\Users\ma_py\AppData\Roaming",
    r"C:\Users\ma_py\.config",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
]

for d in search_dirs:
    for root, dirs, files in os.walk(d):
        for f in files:
            if any(x in f.lower() for x in ["token", "credentials", "client_secret"]):
                fp = os.path.join(root, f)
                if fp.endswith(".json"):
                    try:
                        with open(fp, encoding="utf-8") as fh:
                            data = json.load(fh)
                        keys = list(data.keys()) if isinstance(data, dict) else []
                        if any(
                            x in str(keys) for x in ["client_id", "access_token", "refresh_token", "installed", "web"]
                        ):
                            print(f"発見: {fp}", flush=True)
                            print(f"  keys: {keys[:5]}", flush=True)
                    except:
                        pass
        # AppDataは深く潜りすぎないよう制限
        if root.count(os.sep) - d.count(os.sep) > 3:
            break
print("完了", flush=True)
