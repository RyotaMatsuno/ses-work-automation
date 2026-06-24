#!/usr/bin/env python3
"""mail_pipeline Task 4: jobz-command 経由でのパイプライン起動確認。"""

from __future__ import annotations

import json
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_URL = "http://127.0.0.1:8765"
AUTH_TOKEN = "jobz-terra-2026"
SES_WORK = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Auth-Token": AUTH_TOKEN,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def verify_jobz_run() -> tuple[bool, str]:
    data = _post(
        "/run",
        {
            "cmd": 'set DRY_RUN=1&& python mail_pipeline\\mail_pipeline.py',
            "cwd": SES_WORK,
            "timeout": 90,
        },
    )
    if data.get("returncode") != 0:
        return False, f"exit {data.get('returncode')}: {data.get('stderr', '')}"
    out = data.get("stdout", "")
    ok_markers = ("DRY_RUN", "起動", "別プロセスが実行中", "スキップ")
    if not any(m in out for m in ok_markers):
        return False, f"unexpected output: {out[:200]!r}"
    return True, "jobz-command経由で mail_pipeline 起動 OK"


def main() -> int:
    try:
        ok, msg = verify_jobz_run()
    except Exception as exc:
        print(f"VERIFY NG: {exc}")
        return 1
    print(msg)
    if ok:
        print("VERIFY OK")
        return 0
    print("VERIFY NG")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
