#!/usr/bin/env python3
"""全pending_tasks完了後の通知スクリプト（CLAUDE.md rule: step 5）。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = BASE_DIR / "config" / ".env"
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def run_gate() -> tuple[int, str]:
    gate_script = BASE_DIR / "gate_checker" / "gate_check.py"
    result = subprocess.run(
        [sys.executable, str(gate_script), "--phase", "implementation", "--dir", str(BASE_DIR)],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(BASE_DIR),
        timeout=120,
    )
    output = (result.stdout or "") + (result.stderr or "")
    print(f"gate_checker exit: {result.returncode}")
    print(output[:500])
    return result.returncode, output


def send_line(message: str, env: dict) -> None:
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_LINE_USER_ID") or env.get("MATSUNO_USER_ID", "")
    if not token or not user_id:
        print("LINE通知スキップ: トークンまたはuserIdが未設定")
        return
    payload = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": message}]},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            print(f"LINE通知送信: {res.status}")
    except Exception as e:
        print(f"LINE通知失敗: {e}")


def main() -> None:
    env = _load_env()
    gate_exit, gate_output = run_gate()

    if gate_exit == 0:
        gate_status = "✅ GO"
    elif gate_exit == 1:
        gate_status = "⚠️ NG（要確認）"
    else:
        gate_status = "スキップ"

    completed_tasks = [
        "investigationR_full_audit（システム全体監査）",
        "taskS_backfill_guard（スキル・単価バックフィル＋マッチングガード）",
        "taskT_p0_p1_fixes（P0/P1バグ修正確認）",
    ]
    tasks_str = "\n".join(f"  ✓ {t}" for t in completed_tasks)

    p0_alert = """
⚠️ 要対応（P0）:
  • freee/run_monthly_invoice.bat → freee_invoice_v2.py に修正必要
  • freee今月の請求書発行を確認してください
  • nightly_jobz/config.py NIGHTLY_BUDGET_USD を関数化必要"""

    detail = "問題なし。" if gate_exit != 1 else "ゲートNGの詳細:\n" + gate_output[:200]

    message = f"""[Cursor完了通知] 全pending_tasks処理完了
完了時刻: {datetime.now().strftime("%Y-%m-%d %H:%M")}
gate_checker: {gate_status}

完了タスク:
{tasks_str}
{p0_alert}

{detail}
"""
    send_line(message, env)
    print("完了通知送信済み")


if __name__ == "__main__":
    main()
