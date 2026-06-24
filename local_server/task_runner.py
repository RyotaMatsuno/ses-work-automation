#!/usr/bin/env python3
"""pending_tasks 指示書の保存・完了処理（jobz-command から呼び出し）。"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime

BASE_DIR = os.path.join(
    os.path.expanduser("~"),
    "OneDrive",
    "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7",  # デスクトップ
    "ses_work",
)
PENDING_DIR = os.path.join(BASE_DIR, "pending_tasks")
DONE_DIR = os.path.join(BASE_DIR, "done_tasks")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def get_next_number() -> int:
    """pending_tasks/の既存ファイル数から次の連番を返す"""
    existing = glob.glob(os.path.join(PENDING_DIR, "*.md"))
    existing = [f for f in existing if not f.endswith(".gitkeep")]
    return len(existing) + 1


def _run_gate_on_save(content, title):
    import os
    import subprocess
    import sys
    import tempfile

    base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".md", prefix="gate_tmp_")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        gate_script = os.path.join(base, "gate_checker", "gate_check.py")
        result = subprocess.run(
            [sys.executable, gate_script, "--phase", "requirements", "--file", tmp_path],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            cwd=base,
            timeout=60,
        )
        output = (result.stdout or "") + (result.stderr or "")
        lines = [l for l in output.splitlines() if l.strip()]
        summary = "\n".join(lines[-5:]) if lines else "(出力なし)"
        print(f"[gate] exit={result.returncode}\n{summary}")
        return result.returncode, summary
    except subprocess.TimeoutExpired:
        print("[gate] タイムアウト -> スキップして保存")
        return 2, "timeout"
    except Exception as e:
        print(f"[gate] エラー -> スキップして保存: {e}")
        return 2, str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def _notify_gate_ng(filename, summary):
    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_LINE_USER_ID") or env.get("MATSUNO_USER_ID", "")
    if not token or not user_id:
        return
    message = "\U0001f6ab [gate NG] save blocked\n" + filename + "\n\n" + summary[:300]
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
            print(f"gate NG LINE通知: {res.status}")
    except Exception as e:
        print(f"gate NG LINE通知失敗: {e}")


def save_task(title, content, gate_on_save=True):
    """指示書をpending_tasks/に保存。gate_on_save=True(default)でゲートを自動実行。"""
    os.makedirs(PENDING_DIR, exist_ok=True)
    num = get_next_number()
    filename = f"{num:03d}_{title}.md"
    if gate_on_save:
        exit_code, summary = _run_gate_on_save(content, title)
        if exit_code == 1:
            print(f"[gate NG] {filename} の保存をブロック")
            _notify_gate_ng(filename, summary)
            return f"GATE_NG:{filename}"
        if exit_code == 2:
            print("[gate] スキップ -> そのまま保存")
    filepath = os.path.join(PENDING_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"保存完了（ゲート通過）: {filename}")
    return filename


def _load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = os.path.join(BASE_DIR, "config", ".env")
    if not os.path.exists(env_path):
        return env
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _notify_line(filename: str, gate_exit: int, gate_output: str) -> None:
    """松野のLINEに完了通知を送る"""
    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_LINE_USER_ID") or env.get("MATSUNO_USER_ID", "")

    if not token or not user_id:
        print("LINE通知スキップ: トークンまたはuserIdが未設定")
        return

    if gate_exit == 0:
        gate_status = "✅ GO"
    elif gate_exit == 1:
        gate_status = "⚠️ NG（要確認）"
    else:
        gate_status = "スキップ"

    detail = "問題なし。次のタスクを確認してください。" if gate_exit != 1 else "ゲートNGの詳細:\n" + gate_output[:200]
    message = f"""[Cursor完了通知]
タスク: {filename}
gate_checker: {gate_status}
完了時刻: {datetime.now().strftime("%H:%M")}

{detail}"""

    payload = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": message}]},
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            print(f"LINE通知送信: {res.status}")
    except Exception as e:
        print(f"LINE通知失敗: {e}")


def done_task(filename: str) -> None:
    """完了した指示書をdone_tasks/に移動 → gate_checker実行 → LINE通知"""
    src = os.path.join(PENDING_DIR, filename)
    dst = os.path.join(DONE_DIR, filename)

    os.makedirs(DONE_DIR, exist_ok=True)
    shutil.move(src, dst)
    print(f"移動完了: {filename} → done_tasks/")

    gate_result = subprocess.run(
        [
            sys.executable,
            os.path.join(BASE_DIR, "gate_checker", "gate_check.py"),
            "--phase",
            "implementation",
            "--dir",
            BASE_DIR,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        cwd=BASE_DIR,
    )
    print(f"gate_checker exit: {gate_result.returncode}")
    print(gate_result.stdout)

    _notify_line(filename, gate_result.returncode, gate_result.stdout or "")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    save_parser = subparsers.add_parser("save")
    save_parser.add_argument("--title", required=True)
    save_parser.add_argument("--content", required=True)

    done_parser = subparsers.add_parser("done")
    done_parser.add_argument("--file", required=True)

    args = parser.parse_args()

    if args.command == "save":
        save_task(args.title, args.content)
    elif args.command == "done":
        done_task(args.file)
    else:
        print("Usage: task_runner.py save --title NAME --content TEXT")
        print("       task_runner.py done --file FILENAME")
        sys.exit(1)


if __name__ == "__main__":
    main()
