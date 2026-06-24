# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

results = {}

# 006
try:
    from line_webhook.line_bridge import _line_push_remaining

    results["006 push_or_log"] = f"✅ OK / LINE残={_line_push_remaining()}通"
except Exception as e:
    results["006 push_or_log"] = f"❌ {e}"

# 007
try:
    from line_webhook.line_bridge import handle_router_message

    r1 = handle_router_message("作業進捗", "u", "m", 0)
    r2 = handle_router_message("進捗", "u", "m", 0)
    r3 = handle_router_message("進捗どうですか", "u", "m", 0)
    ok = r1["handled"] and "3種類" in r2["reply"] and not r3["handled"]
    results["007 進捗コマンド"] = f"{'✅ OK' if ok else '❌ NG'}"
except Exception as e:
    results["007 進捗コマンド"] = f"❌ {e}"

# 008
from pathlib import Path

w = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\pending_watcher.py")
results["008 watcher"] = "✅ 存在" if w.exists() else "❌ NOT FOUND"

r = subprocess.run(["schtasks", "/query", "/tn", "SES_PendingWatcher", "/fo", "LIST"], capture_output=True, timeout=10)
out = r.stdout.decode("cp932", errors="replace")
results["008 scheduler"] = "✅ 登録済み" if "準備完了" in out or "実行中" in out else "❌ 未登録"

for k, v in results.items():
    print(f"[{k}] {v}")
