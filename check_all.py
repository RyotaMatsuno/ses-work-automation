# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

results = {}

# 006: push_or_log
try:
    from line_webhook.line_bridge import _line_push_remaining

    results["006_push_or_log"] = f"OK / 残通数={_line_push_remaining()}"
except Exception as e:
    results["006_push_or_log"] = f"NG: {e}"

# 007: 進捗コマンド
try:
    from line_webhook.line_bridge import handle_router_message

    r1 = handle_router_message("作業進捗", "u", "m", 0)
    r2 = handle_router_message("進捗", "u", "m", 0)
    r3 = handle_router_message("案件進捗どう", "u", "m", 0)
    ok1 = r1.get("handled") == True
    ok2 = "3種類" in r2.get("reply", "")
    ok3 = r3.get("handled") == False
    results["007_progress"] = (
        f"{'OK' if all([ok1, ok2, ok3]) else 'NG'} / 作業進捗={ok1} ガイド={ok2} 部分一致スルー={ok3}"
    )
except Exception as e:
    results["007_progress"] = f"NG: {e}"

# 008: pending_watcher.py
from pathlib import Path

watcher = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\pending_watcher.py")
results["008_watcher"] = "存在する" if watcher.exists() else "NOT FOUND"

# 008: タスクスケジューラ
r = subprocess.run(["schtasks", "/query", "/tn", "SES_PendingWatcher", "/fo", "LIST"], capture_output=True, timeout=10)
out = r.stdout.decode("cp932", errors="replace")
if "準備完了" in out or "実行中" in out:
    results["008_scheduler"] = "登録済み・準備完了"
elif r.returncode != 0:
    results["008_scheduler"] = "未登録"
else:
    results["008_scheduler"] = out[:100]

for k, v in results.items():
    print(f"[{k}] {v}")
