"""LINE 通知（push_message ラッパ）。urllib版で外部依存なし。"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_LIMIT = 4500  # LINE単一メッセージ上限

MATSUNO_USER_ID = "Ue3508b43b84991f5a68281da5bf4cf39"
SES_WORK = Path(__file__).resolve().parent.parent


def _load_env() -> dict:
    env_path = SES_WORK / "config" / ".env"
    env = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def push_message(text: str, user_id: str = None) -> tuple[int, str]:
    """LINE push。失敗しても例外を投げない。"""
    env = _load_env()
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return (0, "LINE_CHANNEL_ACCESS_TOKEN未設定")
    uid = user_id or MATSUNO_USER_ID

    body = json.dumps(
        {
            "to": uid,
            "messages": [{"type": "text", "text": text[:LINE_LIMIT]}],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        LINE_PUSH_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (resp.status, resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        return (e.code, e.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        return (0, str(exc))


def notify_success(filename: str, cost_usd: float, duration_sec: float) -> None:
    text = f"✅ [auto_runner] {filename} 完了\n判定: GO\nコスト: ${cost_usd:.4f}\n所要時間: {duration_sec:.0f}秒"
    push_message(text)


def notify_retry(filename: str, try_num: int, reason: str) -> None:
    text = f"🔄 [auto_runner] {filename} NG → 再投入（{try_num}/2回目）\nNG理由: {reason[:500]}"
    push_message(text)


def notify_blocked(filename: str, reason: str) -> None:
    text = f"🚫 [auto_runner] {filename} 2回連続NG → 人間確認要\nNG理由: {reason[:500]}\n場所: blocked_tasks/{filename}"
    push_message(text)


def notify_cost_guard(monthly_usd: float) -> None:
    text = f"⛔ [auto_runner] 月次コスト$140超 → 全作業停止\n今月コスト: ${monthly_usd:.2f}"
    push_message(text)


def notify_timeout(filename: str) -> None:
    text = f"⏱ [auto_runner] {filename} Claude Code タイムアウト\n自動再投入されます"
    push_message(text)


if __name__ == "__main__":
    # 単体テスト
    status, body = push_message("[test] notifier.py 単体テスト")
    print(f"status={status} body={body[:200]}")
