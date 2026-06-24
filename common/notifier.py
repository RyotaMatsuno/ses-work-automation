from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path

from common.io_utils import setup_stdout

setup_stdout()

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"

try:
    from dotenv import dotenv_values as _dotenv_values

    _ENV: dict = _dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}
except ImportError:
    _ENV = {}


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _ENV.get(name, default)


# reason → 優先度（SPEC §10）
_PRIORITY_MAP: dict[str, int] = {
    # priority 1: EMERGENCY（常に通知）
    # priority 2
    "error_model_unavailable_all_fallback": 2,
    "error_internal": 2,
    "error_auth": 2,
    # priority 3
    "stopped_budget": 3,
    "error_permanent_api": 3,
    "error_response_invalid": 3,
    # priority 4
    "stopped_phase_threshold": 4,
    "error_bad_request": 4,
    "error_missing_target_id": 4,
    # priority 5 (log only)
    "stopped_call_limit": 5,
    "error_transient_models_list": 5,
    "error_transient_api": 5,
    "error_model_unavailable_all_fallback": 2,
    # no notification
    "ok": 0,
    "skipped_duplicate": 0,
}

# transient 連続失敗カウンター（phase → count）
_transient_counters: dict[str, int] = {}


def _get_line_token() -> str:
    return _get_env("LINE_CHANNEL_ACCESS_TOKEN", "")


def _get_line_user_id() -> str:
    return _get_env("MATSUNO_LINE_USER_ID", "")


def _get_remaining_line_count() -> int:
    """LINE Messaging API の残送信可能数を返す（取得失敗時は 9999）。"""
    token = _get_line_token()
    if not token:
        return 9999
    try:
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/quota/consumption",
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        quota = data.get("value", 9999)
        total = data.get("totalUsage", 0)
        return max(0, int(quota) - int(total))
    except Exception:
        return 9999


def _send_line(message: str) -> None:
    token = _get_line_token()
    user_id = _get_line_user_id()
    if not token or not user_id:
        logger.info("[notifier] LINE skip (token/user not configured): %s", message[:80])
        return

    body = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": message}]},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("[notifier] LINE sent (status=%d)", resp.status)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        logger.warning("[notifier] LINE error %d: %s", e.code, detail)
    except Exception as e:
        logger.warning("[notifier] LINE error: %s", e)


def notify(
    reason: str,
    detail: str = "",
    phase: str = "",
    block_type: str = "",
) -> None:
    """reason に応じた通知優先度で LINE 送信またはログ記録する（SPEC §10）。"""
    priority = _PRIORITY_MAP.get(reason, 5)

    # transient 連続3回で優先度3に昇格
    if reason.startswith("error_transient_"):
        key = f"{reason}:{phase}"
        _transient_counters[key] = _transient_counters.get(key, 0) + 1
        if _transient_counters[key] >= 3:
            priority = min(priority, 3)
    else:
        # 非 transient が来たらカウンタリセット
        for k in list(_transient_counters.keys()):
            if k.endswith(f":{phase}"):
                _transient_counters[k] = 0

    if priority == 0:
        return

    msg_parts = [f"[CostGuard] reason={reason}"]
    if phase:
        msg_parts.append(f"phase={phase}")
    if block_type:
        msg_parts.append(f"block_type={block_type}")
    if detail:
        msg_parts.append(f"detail={detail}")
    message = " / ".join(msg_parts)

    if priority == 1:
        _send_line(message)
        return

    remaining = _get_remaining_line_count()

    if priority == 2:
        if remaining < 10:
            logger.warning("[notifier] log-only (remaining=%d): %s", remaining, message)
        else:
            _send_line(message)

    elif priority == 3:
        if remaining < 30:
            logger.warning("[notifier] log-only (remaining=%d): %s", remaining, message)
        else:
            _send_line(message)

    elif priority == 4:
        if remaining < 30:
            logger.info("[notifier] log-only (remaining=%d): %s", remaining, message)
        else:
            _send_line(message)

    else:
        logger.info("[notifier] log-only: %s", message)
