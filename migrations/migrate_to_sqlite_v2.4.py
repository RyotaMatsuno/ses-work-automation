"""
migrate_to_sqlite_v2.4.py - cost_state.json から sqlite への一回限り移行スクリプト。

実行方法:
  python migrations/migrate_to_sqlite_v2.4.py

完了後、cost_state.json を cost_state.json.bak_v2.4 にリネームして readonly backup とする。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from common.state_store import init_schema, open_conn

STATE_FILE_OLD = Path(os.environ.get("APPDATA", "")).parent / "Local" / "ses_work_state" / "cost_state.json"
# Legacy path used by old ledger.py
STATE_FILE_LEGACY = Path(os.environ.get("APPDATA", BASE_DIR)).parent / "Local" / "ses_work_state" / "cost_state.json"


def load_old_state() -> dict:
    for candidate in [STATE_FILE_OLD, STATE_FILE_LEGACY]:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                print(f"[migrate] loaded: {candidate}")
                return data, candidate
            except Exception as e:
                print(f"[migrate] failed to read {candidate}: {e}")
    return {}, None


def migrate() -> None:
    print("[migrate] initializing sqlite schema...")
    init_schema()

    old_state, old_path = load_old_state()
    if not old_state:
        print("[migrate] no existing cost_state.json found. Starting fresh.")
        return

    today = old_state.get("date", "")
    month = old_state.get("month", "")
    daily_usd = float(old_state.get("daily_usd", 0.0))
    monthly_usd = float(old_state.get("monthly_usd", 0.0))
    daily_calls = int(old_state.get("daily_calls", 0))

    conn = open_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            if today:
                conn.execute(
                    "INSERT OR REPLACE INTO daily_state(date, daily_usd, daily_calls) VALUES(?,?,?)",
                    (today, daily_usd, daily_calls),
                )
            if month:
                conn.execute(
                    "INSERT OR REPLACE INTO monthly_state(month, monthly_usd) VALUES(?,?)", (month, monthly_usd)
                )
            conn.execute("COMMIT")
            print(
                f"[migrate] imported: date={today} daily_usd={daily_usd} "
                f"monthly_usd={monthly_usd} daily_calls={daily_calls}"
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    # バックアップ作成
    if old_path and old_path.exists():
        bak = old_path.with_suffix(".json.bak_v2.4")
        old_path.rename(bak)
        print(f"[migrate] backup: {old_path} -> {bak}")

    print("[migrate] done.")


if __name__ == "__main__":
    migrate()
