# -*- coding: utf-8 -*-
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

checks = [
    # 006: line_bridge.py に push_or_log があるか
    (
        "006 push_or_log",
        f'python -c "import sys; sys.path.insert(0,r"{SES}"); from line_webhook.line_bridge import push_or_log, _line_push_remaining; print("OK", _line_push_remaining())"',
    ),
    # 007: handle_router_message が進捗コマンドを処理するか
    (
        "007 progress_cmd",
        f'python -c "import sys; sys.path.insert(0,r"{SES}"); from line_webhook.line_bridge import handle_router_message; r=handle_router_message("作業進捗","u","m",0); print("OK" if r["handled"] else "NG")"',
    ),
    # 008: pending_watcher.py が存在するか
    (
        "008 watcher_exists",
        f'python -c "from pathlib import Path; p=Path(r"{SES}/local_server/pending_watcher.py"); print("OK" if p.exists() else "NOT FOUND")"',
    ),
    # 008: タスクスケジューラ登録確認
    ("008 scheduler", "schtasks /query /tn SES_PendingWatcher /fo LIST 2>nul | findstr 状態"),
]

for name, cmd in checks:
    r = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=SES, timeout=15
    )
    out = (r.stdout + r.stderr).strip()[:100]
    print(f"[{name}] {out or '(出力なし)'}")
