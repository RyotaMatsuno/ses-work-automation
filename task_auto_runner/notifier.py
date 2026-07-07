"""LINE 通知（push_message ラッパ）。urllib版で外部依存なし。

通知はダイジェスト方式: イベントを notify_queue.jsonl に追記し、
12:00/18:00 JST に flush_notify_queue() で1通にまとめて送信する。
notify_cost_guard のみ即時push（重大アラート）。
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
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
NOTIFY_QUEUE = Path(__file__).resolve().parent / "notify_queue.jsonl"


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


def _enqueue_event(event_type: str, **kwargs) -> None:
    """イベントを notify_queue.jsonl に追記する。"""
    entry = {"ts": datetime.now().isoformat(), "type": event_type, **kwargs}
    try:
        with open(NOTIFY_QUEUE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def notify_success(filename: str, cost_usd: float, duration_sec: float) -> None:
    _enqueue_event("success", task=filename, cost_usd=cost_usd, duration_sec=duration_sec)


def notify_retry(filename: str, try_num: int, reason: str) -> None:
    _enqueue_event("retry", task=filename, try_num=try_num, reason=reason[:500])


def notify_blocked(filename: str, reason: str) -> None:
    _enqueue_event("blocked", task=filename, reason=reason[:500])


def notify_timeout(filename: str) -> None:
    _enqueue_event("timeout", task=filename)


def notify_cost_guard(monthly_usd: float) -> None:
    # 重大アラートのため即時push（ダイジェスト対象外）
    text = f"⛔ [auto_runner] 月次コスト$140超 → 全作業停止\n今月コスト: ${monthly_usd:.2f}"
    push_message(text)


def flush_notify_queue(label: str = None) -> bool:
    """キューのイベントを1通にまとめてLINE送信し、キューを消し込む。
    0件の場合は送信せずFalseを返す。
    """
    if not NOTIFY_QUEUE.exists():
        return False

    raw = NOTIFY_QUEUE.read_text(encoding="utf-8")
    lines = [l for l in raw.splitlines() if l.strip()]
    if not lines:
        return False

    events = []
    for line in lines:
        try:
            events.append(json.loads(line))
        except Exception:
            pass

    if not events:
        return False

    counts = {"success": 0, "retry": 0, "blocked": 0, "timeout": 0, "gate_ng": 0}
    for e in events:
        t = e.get("type", "")
        if t in counts:
            counts[t] += 1
        elif t in ("gate_ng_blocked", "gate_costguard"):
            counts["gate_ng"] += 1

    if label is None:
        label = datetime.now().strftime("%H:%M")

    header = (
        f"[runner {label}] 完了{counts['success']} / "
        f"再投入{counts['retry']} / blocked {counts['blocked']}"
    )
    if counts["timeout"]:
        header += f" / timeout {counts['timeout']}"
    if counts["gate_ng"]:
        header += f" / gate_ng {counts['gate_ng']}"

    detail_lines = [header]
    for e in events:
        t = e.get("type", "")
        task = e.get("task", "")
        if t == "success":
            cost = e.get("cost_usd", 0)
            dur = e.get("duration_sec", 0)
            detail_lines.append(f"✅ {task} (${cost:.4f}, {dur:.0f}秒)")
        elif t == "retry":
            num = e.get("try_num", "?")
            reason = e.get("reason", "")[:100]
            detail_lines.append(f"🔄 {task} ({num}/2回目 {reason})")
        elif t == "blocked":
            reason = e.get("reason", "")[:100]
            detail_lines.append(f"🚫 {task} → blocked ({reason})")
        elif t == "timeout":
            detail_lines.append(f"⏱ {task} TIMEOUT")
        elif t == "gate_ng":
            phase = e.get("phase", "")
            detail_lines.append(f"🔶 gate NG: {e.get('target', task)} ({phase})")
        elif t == "gate_ng_blocked":
            detail_lines.append(f"⛔ gate 3回到達blocked: {e.get('target', task)}")
        elif t == "gate_costguard":
            detail_lines.append(f"⛔ gate CostGuard停止: {e.get('target', task)}")

    push_message("\n".join(detail_lines))

    # 消し込み（多重送信防止）
    NOTIFY_QUEUE.write_text("", encoding="utf-8")
    return True


if __name__ == "__main__":
    # 単体テスト
    status, body = push_message("[test] notifier.py 単体テスト")
    print(f"status={status} body={body[:200]}")
