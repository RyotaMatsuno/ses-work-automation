# -*- coding: utf-8 -*-
"""LINE instruction router, Notion work queue, and draft-only workers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import dotenv_values
except ImportError:
    dotenv_values = None

_ENV_PATH = Path(__file__).resolve().parent.parent / "config" / ".env"
_DEFAULT_QUEUE_DB_ID = "37a450ff-37c0-819a-981b-c2e06ed282bb"
_DEFAULT_ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
_HUMAN_REVIEW_FILE = Path(__file__).resolve().parent.parent / "local_server" / "human_review_items.json"
_TASK_REPLY_RE = re.compile(r"^#(T\d+)\s+(.+)$", re.DOTALL)
_QUESTION_PATTERNS = (
    re.compile(r"質問[:：]\s*(.+)", re.DOTALL),
    re.compile(r"確認[:：]\s*(.+)", re.DOTALL),
    re.compile(r"【質問】\s*(.+)", re.DOTALL),
)

JST = timezone(timedelta(hours=9))
REPLY_ONLY_THRESHOLD = 150
_PUSH_SKIP_LOG = Path(__file__).resolve().parent.parent / "usage_tracker" / "line_push_skipped.jsonl"
_PUSH_ERROR_LOG = Path(__file__).resolve().parent.parent / "logs" / "push_errors.log"
NOTION_VERSION = "2022-06-28"
MATSUNO_USER_ID = os.environ.get("MATSUNO_LINE_USER_ID", "Ue3508b43b84991f5a68281da5bf4cf39")
MODEL = os.environ.get("LINE_BRIDGE_MODEL", "claude-haiku-4-5-20251001")
CLAUDE_MODEL = MODEL

_CONFIRMATIONS: dict[str, dict[str, Any]] = {}
_CONFIRMATION_TTL_SECONDS = 600
_HANDOFF_MARKERS = ("■", "【", "】", "最優先", "未完了")
_HANDOFF_SECTION_RE = re.compile(r"■\s*(?:最優先|未完了[・･]?続きが必要なもの|次チャットで最初にやること)")
_HANDOFF_BULLET_RE = re.compile(r"^\s*(?:[-－ー•·]|・|\d+[.)．、])\s*(.+?)\s*$")
_HANDOFF_ROUTE = {
    "route": "research",
    "kind": "research",
    "assignee": "jobz",
    "human_confirmation": "不要",
}
_DEV_BLOCKED_REASON = "手動対応が必要: Cursorで実行してください"


class CostLimitError(RuntimeError):
    pass


ROUTE_CHOICES = {
    "1": "sales",
    "営業": "sales",
    "2": "accounting",
    "経理": "accounting",
    "3": "development",
    "開発": "development",
    "4": "immediate",
    "即時": "immediate",
}
SENSITIVE_WORDS = (
    "送信",
    "メールして",
    "請求",
    "確定",
    "契約",
    "本番",
    "更新",
    "登録",
    "freee",
    "入金消込",
)
SALES_HEAVY_WORDS = (
    "重作業",
    "深掘り",
    "提案文まで",
    "提案文作成",
    "評価表",
    "意向確認文",
    "面談調整",
)
ACCOUNTING_WORDS = (
    "請求",
    "入金",
    "契約マスター",
    "試算",
    "節税",
    "法人化",
    "払出",
    "freee",
)
DEVELOPMENT_WORDS = (
    "costguard",
    "cursor",
    "codex",
    "claude code",
    "開発",
    "コード",
    "バグ",
    "修正して",
    "実装して",
)
IMMEDIATE_WORDS = (
    "今日の案件",
    "この人どう",
    "マッチング",
    "案件一覧",
    "人材一覧",
    "進捗",
    "案件",
    "人材",
    "スキルシート",
    "この人",
)


def _ensure_env_loaded() -> None:
    if os.environ.get("NOTION_API_KEY") or dotenv_values is None:
        return
    if not _ENV_PATH.exists():
        return
    for key, value in dotenv_values(_ENV_PATH).items():
        if value and key not in os.environ:
            os.environ[key] = value


def _line_push_remaining() -> int:
    """今月のLINE push残通数を返す。エラー時は-1。"""
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return -1
    try:
        r_quota = requests.get(
            "https://api.line.me/v2/bot/message/quota",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        r_used = requests.get(
            "https://api.line.me/v2/bot/message/quota/consumption",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if r_quota.status_code == 200 and r_used.status_code == 200:
            return max(0, r_quota.json().get("value", 200) - r_used.json().get("totalUsage", 0))
    except Exception:
        pass
    return -1


def _send_line_push_raw(user_id: str, text: str) -> bool:
    """LINE push送信。成功したらTrue。"""
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return False
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": user_id, "messages": [{"type": "text", "text": text}]},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def get_human_review_items() -> list[str]:
    """松野への確認・報告事項を読み込む。"""
    try:
        if _HUMAN_REVIEW_FILE.exists():
            data = json.loads(_HUMAN_REVIEW_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def add_human_review_item(item: str) -> None:
    """確認・報告事項を追加する（ジョブズからのみ呼ぶ）。"""
    items = get_human_review_items()
    now = datetime.now(JST).strftime("%m/%d %H:%M")
    items.append(f"[{now}] {item}")
    # 最大10件まで保持
    items = items[-10:]
    _HUMAN_REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HUMAN_REVIEW_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_human_review_items() -> None:
    """確認事項をクリアする（松野が確認済みのとき）。"""
    try:
        _HUMAN_REVIEW_FILE.write_text("[]", encoding="utf-8")
    except Exception:
        pass


def _log_push_skipped(text: str, reason: str) -> None:
    """pushを送らず内容だけファイルに記録する。"""
    try:
        _PUSH_SKIP_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(JST).isoformat(),
            "reason": reason,
            "text": text[:2000],
        }
        with _PUSH_SKIP_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _log_push_error(user_id: str, text: str, reason: str, task_id: str = "") -> None:
    """LINE push失敗・通知未達を専用ログに記録する（Notionキューには投入しない）。"""
    try:
        _PUSH_ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(JST).isoformat(),
            "reason": reason,
            "line_user_id": user_id,
            "task_id": task_id,
            "text": text[:2000],
        }
        with _PUSH_ERROR_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _handle_push_unavailable(user_id: str, text: str, reason: str, task_id: str) -> str:
    """push不可時: 専用ログ記録。既存タスクがあれば結果リンクのみ更新。"""
    _log_push_error(user_id, text, reason, task_id)
    if not task_id:
        return "error_logged"
    try:
        page = _find_task(task_id)
        if not page:
            return "error_logged"
        now = datetime.now(JST)
        existing = _extract_text(page.get("properties", {}).get("結果リンク", {}))
        _update_page(
            page["id"],
            {
                "結果リンク": _rich_text(
                    existing + f"\n[通知未達 {now.strftime('%H:%M')}] {reason}。Claude.aiで確認してください。"
                )
            },
        )
        return "notion_logged"
    except Exception:
        return "failed"


def push_or_log(user_id: str, text: str, task_id: str = "") -> str:
    """
    LINE残通数を確認してpushを試みる。
    残0・quota取得失敗・reply-only(≤150通)の場合はpushせずログに記録する。
    戻り値: 'pushed' | 'notion_logged' | 'error_logged' | 'failed'
    """
    remaining = _line_push_remaining()
    if remaining == -1:
        reason = "LINE quota取得失敗"
        print(f"[line_bridge] {reason} - pushスキップしてログのみ記録")
        _log_push_skipped(text, reason)
        return _handle_push_unavailable(user_id, text, reason, task_id)
    if remaining <= REPLY_ONLY_THRESHOLD:
        reason = f"reply-onlyモード (残{remaining}通)"
        print(f"[line_bridge] {reason} - ログのみ")
        _log_push_skipped(text, reason)
        return _handle_push_unavailable(user_id, text, reason, task_id)
    if remaining > 0:
        if _send_line_push_raw(user_id, text):
            return "pushed"
        reason = "LINE push失敗"
        return _handle_push_unavailable(user_id, text, reason, task_id)
    reason = f"LINE push失敗（残{remaining}通）"
    return _handle_push_unavailable(user_id, text, reason, task_id)


def _queue_db_id() -> str:
    _ensure_env_loaded()
    return os.environ.get("NOTION_AI_QUEUE_DB_ID", _DEFAULT_QUEUE_DB_ID)


class CostGuard:
    """Cost guard with kill switch and daily/monthly/batch limits."""

    _lock = threading.Lock()
    _state_path = Path(os.environ.get("LINE_BRIDGE_COST_STATE", "/tmp/line_bridge_cost.json"))
    _batch_calls = 0
    _batch_active = False

    @classmethod
    def _load(cls) -> dict[str, Any]:
        now = datetime.now(JST)
        state = {
            "date": now.strftime("%Y-%m-%d"),
            "month": now.strftime("%Y-%m"),
            "daily_usd": 0.0,
            "monthly_usd": 0.0,
        }
        try:
            loaded = json.loads(cls._state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state.update(loaded)
        except (OSError, ValueError, TypeError):
            pass
        if state.get("month") != now.strftime("%Y-%m"):
            state.update(
                month=now.strftime("%Y-%m"),
                date=now.strftime("%Y-%m-%d"),
                daily_usd=0.0,
                monthly_usd=0.0,
            )
        elif state.get("date") != now.strftime("%Y-%m-%d"):
            state.update(date=now.strftime("%Y-%m-%d"), daily_usd=0.0)
        return state

    @classmethod
    def _save(cls, state: dict[str, Any]) -> None:
        cls._state_path.parent.mkdir(parents=True, exist_ok=True)
        cls._state_path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def begin_batch(cls) -> None:
        with cls._lock:
            cls._batch_calls = 0
            cls._batch_active = True

    @classmethod
    def end_batch(cls) -> None:
        with cls._lock:
            cls._batch_active = False
            cls._batch_calls = 0

    @classmethod
    def reserve(cls, max_tokens: int, caller: str) -> None:
        if os.environ.get("LLM_KILL", "0") == "1":
            raise RuntimeError("CostGuard: LLM_KILL is active")
        estimated = (2000 * 1.0 + max_tokens * 5.0) / 1_000_000
        daily_limit = float(os.environ.get("LINE_BRIDGE_DAILY_USD", "1.0"))
        monthly_limit = float(os.environ.get("LINE_BRIDGE_MONTHLY_USD", "6.0"))
        with cls._lock:
            state = cls._load()
            if float(state["daily_usd"]) + estimated > daily_limit:
                raise CostLimitError("CostGuard: daily limit exceeded")
            if float(state["monthly_usd"]) + estimated > monthly_limit:
                raise CostLimitError("CostGuard: monthly limit exceeded")
            state["daily_usd"] = round(float(state["daily_usd"]) + estimated, 8)
            state["monthly_usd"] = round(float(state["monthly_usd"]) + estimated, 8)
            state["last_caller"] = caller
            if cls._batch_active:
                cls._batch_calls += 1
            cls._save(state)

    @classmethod
    def can_call(cls) -> bool:
        if os.environ.get("LLM_KILL", "0") == "1":
            return False
        daily_limit = float(os.environ.get("LINE_BRIDGE_DAILY_USD", "1.0"))
        monthly_limit = float(os.environ.get("LINE_BRIDGE_MONTHLY_USD", "6.0"))
        with cls._lock:
            state = cls._load()
            return float(state["daily_usd"]) < daily_limit and float(state["monthly_usd"]) < monthly_limit

    @classmethod
    def record(
        cls,
        input_tokens: int,
        output_tokens: int,
        model: str,
        caller: str,
    ) -> None:
        model_name = (model or "").lower()
        rates = (3.0, 15.0) if "sonnet" in model_name else (1.0, 5.0)
        cost = (max(input_tokens, 0) * rates[0] + max(output_tokens, 0) * rates[1]) / 1_000_000
        with cls._lock:
            state = cls._load()
            state["daily_usd"] = round(float(state["daily_usd"]) + cost, 8)
            state["monthly_usd"] = round(float(state["monthly_usd"]) + cost, 8)
            state["last_caller"] = caller
            cls._save(state)


def cost_guard_can_call() -> bool:
    return CostGuard.can_call()


def cost_guard_record(
    input_tokens: int,
    output_tokens: int,
    model: str,
    caller: str,
) -> None:
    CostGuard.record(input_tokens, output_tokens, model, caller)


def guarded_anthropic_call(
    system: str,
    content: Any,
    max_tokens: int,
    caller: str,
    model: str = MODEL,
) -> str:
    """Call Anthropic only after CostGuard reserves estimated cost."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    CostGuard.reserve(max_tokens=max_tokens, caller=caller)
    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": content}],
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage", {})
    print(
        f"[line_bridge_llm] caller={caller} model={model} "
        f"in={usage.get('input_tokens', '?')} "
        f"out={usage.get('output_tokens', '?')}"
    )
    return data["content"][0]["text"]


def _notion_headers() -> dict[str, str]:
    _ensure_env_loaded()
    api_key = os.environ.get("NOTION_API_KEY", "")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY is not configured")
    if not _queue_db_id():
        raise RuntimeError("NOTION_AI_QUEUE_DB_ID is not configured")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def _notion_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.request(
        method,
        f"https://api.notion.com/v1/{path}",
        headers=_notion_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Notion API {response.status_code}: {response.text[:300]}")
    return response.json()


def _title(value: str) -> dict[str, Any]:
    return {"title": [{"text": {"content": value[:2000]}}]}


def _rich_text(value: str) -> dict[str, Any]:
    chunks = [value[index : index + 2000] for index in range(0, min(len(value), 20000), 2000)]
    return {"rich_text": [{"text": {"content": chunk}} for chunk in chunks]}


def _select(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


def _date(value: datetime) -> dict[str, Any]:
    return {"date": {"start": value.isoformat()}}


def _extract_text(prop: dict[str, Any]) -> str:
    values = prop.get("title") or prop.get("rich_text") or []
    return "".join(item.get("plain_text", "") for item in values)


def _extract_select(prop: dict[str, Any]) -> str:
    return (prop.get("select") or {}).get("name", "")


# イニシャル+地名パターン: PH 京成小岩 / A.B 渋谷 / SK 北本 → 人員確定メッセージ
_INITIAL_PLACE_RE = re.compile(r"^/?([A-Za-z]{1,2}(?:\.[A-Za-z]{1,2})?)\s+[　-鿿゠-ヿ＀-￯一-鿿].{0,20}$")

_CANDIDATE_FIELD_PATTERNS: dict[str, str] = {
    "name": r"【(?:名前|氏名)】\s*([^\n【]+)",
    "station": r"【(?:最寄|最寄り駅?)】\s*([^\n【]+)",
    "price": r"【(?:単価|希望単価)】\s*(\d+)万",
    "start_date": r"【(?:開始日?|稼働)】\s*([^\n【]+)",
    "skills": r"【(?:スキル|技術)】\s*([^\n【]+)",
}


def _parse_candidate_text(text: str) -> dict | None:
    result: dict = {}
    for key, pat in _CANDIDATE_FIELD_PATTERNS.items():
        m = re.search(pat, text, re.DOTALL)
        if m:
            result[key] = m.group(1).strip()

    if not result.get("name"):
        return None

    age_m = re.search(r"(\d+歳[/／]?(?:男性|女性))", text)
    if age_m:
        result["age_gender"] = age_m.group(1)

    if result.get("skills"):
        result["skills"] = [s.strip() for s in re.split(r"[,、/|]", result["skills"]) if s.strip()]

    url_m = re.search(r"https://(?:docs|drive)\.google\.com/[^\s]+", text)
    if url_m:
        result["sheet_url"] = url_m.group()

    return result


def _check_duplicate_engineer(name: str, station: str) -> bool:
    if not name:
        return False
    try:
        _ensure_env_loaded()
        api_key = os.environ.get("NOTION_API_KEY", "")
        if not api_key:
            return False
        engineer_db = os.environ.get("NOTION_ENGINEER_DB_ID", _DEFAULT_ENGINEER_DB_ID)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{engineer_db}/query",
            headers=headers,
            json={"filter": {"property": "名前", "title": {"equals": name}}, "page_size": 5},
            timeout=15,
        )
        if resp.status_code != 200:
            return False
        for eng in resp.json().get("results", []):
            props = eng.get("properties", {})
            st = props.get("最寄り駅", {}).get("rich_text", [])
            existing_station = st[0].get("plain_text", "") if st else ""
            if station and station in existing_station:
                return True
    except Exception:
        pass
    return False


def classify_route(text: str) -> dict[str, str]:
    normalized = text.strip().lower()
    stripped = text.strip()

    # ★ URL + 候補者フォーマット検知（最優先 — DEVELOPMENT_WORDS等より前に評価）
    has_sheet_url = bool(re.search(r"https://docs\.google\.com/spreadsheets/", stripped))
    has_drive_url = bool(re.search(r"https://(?:docs|drive)\.google\.com/", stripped))
    has_candidate_format = bool(re.search(r"【(?:名前|氏名|イニシャル)】", stripped))
    if has_sheet_url or (has_drive_url and has_candidate_format) or has_candidate_format:
        return {
            "route": "candidate_intake",
            "kind": "engineer_registration",
            "assignee": "jobz",
            "human_confirmation": "不要",
        }

    # イニシャル+地名 → 人員確定として即時マッチング
    if _INITIAL_PLACE_RE.match(stripped):
        return {
            "route": "immediate",
            "kind": "matching",
            "assignee": "matching_v3",
            "human_confirmation": "不要",
        }
    if normalized.startswith("/"):
        return {
            "route": "immediate",
            "kind": "matching",
            "assignee": "matching_v3",
            "human_confirmation": "不要",
        }
    confirmation = "要" if any(word.lower() in normalized for word in SENSITIVE_WORDS) else "不要"
    if any(word.lower() in normalized for word in ACCOUNTING_WORDS):
        return {
            "route": "accounting",
            "kind": "billing",
            "assignee": "shibusawa",
            "human_confirmation": confirmation,
        }
    if any(word.lower() in normalized for word in DEVELOPMENT_WORDS):
        assignee = "codex" if "codex" in normalized else "cursor"
        return {
            "route": "development",
            "kind": "dev",
            "assignee": assignee,
            "human_confirmation": confirmation,
        }
    if any(word.lower() in normalized for word in SALES_HEAVY_WORDS):
        return {
            "route": "sales",
            "kind": "proposal",
            "assignee": "girard",
            "human_confirmation": confirmation,
        }
    if any(word.lower() in normalized for word in IMMEDIATE_WORDS):
        return {
            "route": "immediate",
            "kind": "matching",
            "assignee": "matching_v3",
            "human_confirmation": "不要",
        }
    if len(normalized) >= 80:
        return {
            "route": "immediate",
            "kind": "matching",
            "assignee": "matching_v3",
            "human_confirmation": "不要",
        }
    return {
        "route": "ambiguous",
        "kind": "",
        "assignee": "",
        "human_confirmation": confirmation,
    }


def _route_from_confirmation(choice: str, original: str) -> dict[str, str] | None:
    route = ROUTE_CHOICES.get(choice.strip().lower())
    if not route:
        return None
    confirmation = "要" if any(word in original for word in SENSITIVE_WORDS) else "不要"
    if route == "sales":
        return {
            "route": route,
            "kind": "proposal",
            "assignee": "girard",
            "human_confirmation": confirmation,
        }
    if route == "accounting":
        return {
            "route": route,
            "kind": "billing",
            "assignee": "shibusawa",
            "human_confirmation": "要",
        }
    if route == "development":
        return {
            "route": route,
            "kind": "dev",
            "assignee": "codex",
            "human_confirmation": confirmation,
        }
    return {
        "route": route,
        "kind": "matching",
        "assignee": "matching_v3",
        "human_confirmation": "不要",
    }


def _task_id(user_id: str, message_id: str, event_timestamp_ms: int) -> str:
    timestamp_min = datetime.fromtimestamp(event_timestamp_ms / 1000, tz=JST).strftime("%Y%m%d%H%M")
    source = f"{user_id}{message_id}{timestamp_min}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()[:16]


def _find_task(task_id: str) -> dict[str, Any] | None:
    db_id = _queue_db_id()
    normalized = task_id.lstrip("#").strip()
    for candidate in (normalized, task_id):
        if not candidate:
            continue
        data = _notion_request(
            "POST",
            f"databases/{db_id}/query",
            {
                "filter": {
                    "property": "task_id",
                    "title": {"equals": candidate},
                },
                "page_size": 1,
            },
        )
        results = data.get("results", [])
        if results:
            return results[0]
    return None


def _extract_question_from_input(raw: str) -> str:
    if not raw.strip():
        return "(質問なし)"
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("question", "質問", "confirm_question", "human_question"):
                value = data.get(key)
                if value:
                    return str(value).strip()[:500]
            text = str(data.get("text", "")).strip()
            if text:
                for pattern in _QUESTION_PATTERNS:
                    match = pattern.search(text)
                    if match:
                        return match.group(1).strip()[:500]
                return text[:300]
    except (ValueError, TypeError):
        pass
    for pattern in _QUESTION_PATTERNS:
        match = pattern.search(raw)
        if match:
            return match.group(1).strip()[:500]
    return raw.strip()[:300]


def _review_task_record(page: dict[str, Any]) -> dict[str, str]:
    props = page.get("properties", {})
    task_id = _extract_text(props.get("task_id", {})) or _extract_text(props.get("タスクID", {}))
    summary = _extract_text(props.get("タスク概要", {}))
    if not summary:
        raw_input = _extract_text(props.get("入力データ", {}))
        try:
            metadata = json.loads(raw_input)
            if isinstance(metadata, dict):
                summary = str(metadata.get("text", ""))[:80]
        except (ValueError, TypeError):
            summary = raw_input[:80]
    return {
        "page_id": page["id"],
        "task_id": task_id,
        "assignee": _extract_select(props.get("担当", {})),
        "summary": summary or "(件名なし)",
        "question": _extract_question_from_input(_extract_text(props.get("入力データ", {}))),
    }


def get_review_tasks() -> list[dict[str, str]]:
    """Fetch review tasks that require human confirmation."""
    data = _notion_request(
        "POST",
        f"databases/{_queue_db_id()}/query",
        {
            "filter": {
                "and": [
                    {"property": "状態", "select": {"equals": "review"}},
                    {"property": "人間確認", "select": {"equals": "要"}},
                ]
            },
            "sorts": [{"property": "作成日時", "direction": "ascending"}],
            "page_size": 100,
        },
    )
    return [_review_task_record(page) for page in data.get("results", [])]


def _format_review_task_block(task: dict[str, str]) -> str:
    task_id = task["task_id"]
    return (
        f"❓【回答待ち #{task_id}】\n"
        f"担当: {task['assignee']}\n"
        f"件名: {task['summary']}\n"
        f"質問: {task['question']}\n"
        f"返信方法: 「#{task_id} {{回答}}」と送ってください"
    )


def handle_task_reply(text: str) -> dict[str, str] | None:
    """Resume a review task by writing the human answer back to Notion."""
    match = _TASK_REPLY_RE.match(text.strip())
    if not match:
        return None
    task_id, answer = match.group(1), match.group(2).strip()
    if not answer:
        return {
            "action": "reply",
            "text": f"回答を入力してください。例: #{task_id} 65万で",
        }
    page = _find_task(task_id)
    if not page:
        return {
            "action": "reply",
            "text": f"タスク {task_id} が見つかりません",
        }
    _update_page(
        page["id"],
        {
            "結果リンク": _rich_text(answer),
            "状態": _select("queued"),
        },
    )
    return {"action": "reply", "text": f"#{task_id} を再開します"}


def _is_handoff_message(text: str) -> bool:
    return any(marker in text for marker in _HANDOFF_MARKERS)


def _extract_handoff_tasks(text: str) -> list[str]:
    matches = list(_HANDOFF_SECTION_RE.finditer(text))
    if not matches:
        return []
    tasks: list[str] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section_body = text[start:end]
        for line in section_body.splitlines():
            bullet = _HANDOFF_BULLET_RE.match(line.strip())
            if not bullet:
                continue
            item = bullet.group(1).strip()
            if item:
                tasks.append(item)
    return tasks


def parse_handoff_message(
    text: str,
    user_id: str,
    reply_token: str,
    event_timestamp_ms: int,
    message_id: str = "",
) -> dict[str, str] | None:
    """Parse Claude handoff messages and enqueue research tasks for jobz."""
    if not _is_handoff_message(text):
        return None
    items = _extract_handoff_tasks(text)
    if not items:
        return None
    created_count = 0
    for index, item in enumerate(items):
        item_message_id = f"{message_id}:handoff:{index}"
        created, _task_id = enqueue_task(
            item,
            _HANDOFF_ROUTE,
            user_id,
            item_message_id,
            event_timestamp_ms,
            reply_token,
        )
        if created:
            created_count += 1
    return {
        "action": "reply",
        "text": f"{created_count}件をキューに登録しました",
    }


def enqueue_task(
    text: str,
    route: dict[str, str],
    user_id: str,
    message_id: str,
    event_timestamp_ms: int,
    reply_token: str,
) -> tuple[bool, str]:
    task_id = _task_id(user_id, message_id, event_timestamp_ms)
    if _find_task(task_id):
        return False, task_id
    metadata = {
        "text": text,
        "line_user_id": user_id,
        "reply_token": reply_token,
        "event_timestamp_ms": event_timestamp_ms,
    }
    now = datetime.now(JST)
    is_dev = route.get("kind") == "dev"
    properties = {
        "task_id": _title(task_id),
        "受付元": _select("LINE"),
        "種別": _select(route["kind"]),
        "優先度": _select("中"),
        "締切": _select("今日中"),
        "入力データ": _rich_text(json.dumps(metadata, ensure_ascii=False)),
        "使用許可": _select("draft-only"),
        "担当": _select(route["assignee"]),
        "状態": _select("blocked" if is_dev else "queued"),
        "コスト見込み": {"number": 0.01},
        "結果リンク": _rich_text(f"blocked: {_DEV_BLOCKED_REASON}" if is_dev else ""),
        "人間確認": _select(route["human_confirmation"]),
        "作成日時": _date(now),
    }
    if is_dev:
        properties["完了日時"] = _date(now)
    _notion_request(
        "POST",
        "pages",
        {
            "parent": {"database_id": _queue_db_id()},
            "properties": properties,
        },
    )
    return True, task_id


def route_line_message(
    text: str,
    user_id: str,
    message_id: str,
    event_timestamp_ms: int,
    reply_token: str,
) -> dict[str, str]:
    """Return action=pass/reply. Only Matsuno can enqueue work."""
    if user_id != MATSUNO_USER_ID:
        return {"action": "pass"}
    stripped = text.strip()
    if stripped.startswith(("/run ", "/bg ")) or stripped in ("/log", "/health"):
        return {"action": "pass"}
    task_reply = handle_task_reply(stripped)
    if task_reply is not None:
        return task_reply
    handoff = parse_handoff_message(
        stripped,
        user_id,
        reply_token,
        event_timestamp_ms,
        message_id,
    )
    if handoff is not None:
        return handoff
    if not stripped:
        return {"action": "reply", "text": "テキストで指示を送ってください。"}
    now = datetime.now(JST).timestamp()
    pending = _CONFIRMATIONS.get(user_id)
    if pending and now - pending["created_at"] > _CONFIRMATION_TTL_SECONDS:
        _CONFIRMATIONS.pop(user_id, None)
        pending = None
    if pending:
        _CONFIRMATIONS.pop(user_id, None)
        route = _route_from_confirmation(text, str(pending["text"]))
        if not route:
            return {
                "action": "reply",
                "text": "判定できないためキュー未登録です。",
            }
        if route["route"] == "immediate":
            return {"action": "immediate", "text": str(pending["text"])}
        created, task_id = enqueue_task(
            str(pending["text"]),
            route,
            user_id,
            str(pending["message_id"]),
            int(pending["event_timestamp_ms"]),
            reply_token,
        )
        return {
            "action": "reply",
            "text": _enqueue_reply(created, task_id, route["assignee"], route.get("kind", "")),
        }

    route = classify_route(text)
    if route["route"] == "candidate_intake":
        eng_info = _parse_candidate_text(text)
        if eng_info:
            if _check_duplicate_engineer(eng_info.get("name", ""), eng_info.get("station", "")):
                return {
                    "action": "reply",
                    "text": (
                        f"既に登録済みのエンジニアです。\n"
                        f"名前: {eng_info['name']}\n"
                        f"最寄り: {eng_info.get('station', '不明')}"
                    ),
                }
            created, task_id = enqueue_task(text, route, user_id, message_id, event_timestamp_ms, reply_token)
            skills = eng_info.get("skills", [])
            skills_str = ", ".join(skills[:5]) if isinstance(skills, list) else str(skills)
            reply_parts = ["候補者を検出しました。", f"名前: {eng_info['name']}"]
            if eng_info.get("price"):
                reply_parts.append(f"単価: {eng_info['price']}万")
            if skills_str:
                reply_parts.append(f"スキル: {skills_str}")
            reply_parts.append(f"\nキューに登録しました。\ntask_id: {task_id}")
            return {"action": "reply", "text": "\n".join(reply_parts)}
        # フォーマット解析失敗でも受け付ける
        created, task_id = enqueue_task(text, route, user_id, message_id, event_timestamp_ms, reply_token)
        return {
            "action": "reply",
            "text": f"候補者情報として受け付けました。\ntask_id: {task_id}",
        }
    if route["route"] == "immediate":
        return {"action": "pass"}
    if route["route"] == "ambiguous":
        _CONFIRMATIONS[user_id] = {
            "text": text,
            "created_at": now,
            "message_id": message_id,
            "event_timestamp_ms": event_timestamp_ms,
            "reply_token": reply_token,
        }
        return {
            "action": "reply",
            "text": ("種別を1つ選んで返信してください。\n1 営業重作業 / 2 経理 / 3 開発 / 4 即時マッチング"),
        }
    created, task_id = enqueue_task(text, route, user_id, message_id, event_timestamp_ms, reply_token)
    return {
        "action": "reply",
        "text": _enqueue_reply(created, task_id, route["assignee"], route.get("kind", "")),
    }


def handle_router_message(
    text: str,
    user_id: str,
    message_id: str,
    event_timestamp_ms: int,
) -> dict[str, Any]:
    """Compatibility adapter used by the existing webhook integration."""
    stripped = text.strip()

    # 完全一致コマンド（最優先・マッチング判定より前に処理）
    if stripped == "作業進捗":
        return {"handled": True, "reply": build_queue_progress(limit=10)}
    if stripped == "進捗":
        return {
            "handled": True,
            "reply": (
                "進捗コマンドは3種類あります:\n"
                "・作業進捗 → AIキューの作業状況\n"
                "・案件進捗 → 案件DBの状況（準備中）\n"
                "・人員進捗 → エンジニアの稼働状況（準備中）"
            ),
        }
    if stripped == "確認済み":
        clear_human_review_items()
        return {"handled": True, "reply": "確認事項をクリアしました✅"}

    if stripped == "案件進捗":
        return {"handled": True, "reply": "案件進捗機能は準備中です。"}
    if stripped == "人員進捗":
        return {"handled": True, "reply": "人員進捗機能は準備中です。"}

    # 既存処理
    if stripped.startswith(("/run ", "/bg ")) or stripped in ("/log", "/health"):
        return {"handled": False}
    result = route_line_message(
        text=stripped,
        user_id=user_id,
        message_id=message_id,
        event_timestamp_ms=event_timestamp_ms,
        reply_token="",
    )
    if result.get("action") == "reply":
        return {"handled": True, "reply": result["text"]}
    return {"handled": False}


def _enqueue_reply(created: bool, task_id: str, assignee: str, kind: str = "") -> str:
    if not created:
        return f"既にキュー登録済みです。\ntask_id: {task_id}"
    if kind == "dev":
        return "開発系タスクとして受け取りました。Claude.aiのCursorウィンドウで対応してください（自動処理対象外）"
    return f"作業キューに登録しました。\ntask_id: {task_id}\n担当: {assignee}"


def _query_queued(limit: int) -> list[dict[str, Any]]:
    data = _notion_request(
        "POST",
        f"databases/{_queue_db_id()}/query",
        {
            "filter": {
                "and": [
                    {
                        "property": "状態",
                        "select": {"equals": "queued"},
                    },
                    {
                        "or": [
                            {
                                "property": "担当",
                                "select": {"equals": "girard"},
                            },
                            {
                                "property": "担当",
                                "select": {"equals": "shibusawa"},
                            },
                        ]
                    },
                ]
            },
            "sorts": [{"property": "作成日時", "direction": "ascending"}],
            "page_size": limit,
        },
    )
    return data.get("results", [])


def _update_page(page_id: str, properties: dict[str, Any]) -> dict[str, Any]:
    return _notion_request("PATCH", f"pages/{page_id}", {"properties": properties})


def _task_payload(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})
    raw = _extract_text(props.get("入力データ", {}))
    try:
        metadata = json.loads(raw)
    except (ValueError, TypeError):
        metadata = {"text": raw}
    return {
        "page_id": page["id"],
        "task_id": _extract_text(props.get("task_id", {})),
        "assignee": _extract_select(props.get("担当", {})),
        "human_confirmation": _extract_select(props.get("人間確認", {})),
        "metadata": metadata,
    }


def _worker_prompt(assignee: str, text: str) -> tuple[str, str]:
    if assignee == "girard":
        system = """あなたはSES営業専任のジラード。draft-only。
粗利フロアは松野5万円・岡本3万円。人材鮮度3週間、案件鮮度4営業日。
外国籍、地方、短期連続、ブランク、既往歴は提案対象外。
スキルシートにない経験を追加しない。送信・DB更新・契約確定はしない。
出力: 判定、根拠、懸念点、追加確認、成果物ドラフト。"""
        return system, f"次の営業依頼をドラフト化してください。\n{text[:12000]}"
    if assignee == "shibusawa":
        system = """あなたは経理/CFO専任の渋沢。draft-only。
数字は入力に明示された契約マスター由来の値だけを使う。不明は不明と書く。
計算根拠を示し、確認事項は1点に絞る。
freee確定、送信、入金消込、本番DB更新、契約確定はしない。"""
        return system, f"次の経理依頼の確認用ドラフトを作成してください。\n{text[:12000]}"
    raise RuntimeError(f"no automatic worker for assignee={assignee}")


def _validate_draft(result: str) -> None:
    if not result.strip():
        raise RuntimeError("worker returned an empty draft")
    prohibited = ("送信しました", "確定しました", "更新しました", "登録しました")
    if any(word in result for word in prohibited):
        raise RuntimeError("draft validation failed: execution claim detected")


def _run_worker(task: dict[str, Any]) -> str:
    system, user = _worker_prompt(task["assignee"], str(task["metadata"].get("text", "")))
    result = guarded_anthropic_call(
        system,
        user,
        max_tokens=1200,
        caller=f"line_bridge_{task['assignee']}",
    )
    _validate_draft(result)
    return result


def _process_single_task(page: dict[str, Any]) -> dict[str, str] | None:
    """Claim one queued task and run its worker (thread-safe via CAS on status)."""
    task = _task_payload(page)
    try:
        _update_page(task["page_id"], {"状態": _select("running")})
        latest = _notion_request("GET", f"pages/{task['page_id']}")
        status = _extract_select(latest.get("properties", {}).get("状態", {}))
        if status != "running":
            return None
        result = _run_worker(task)
        final_status = "review" if task["human_confirmation"] == "要" else "done"
        _update_page(
            task["page_id"],
            {
                "状態": _select(final_status),
                "結果リンク": _rich_text(result),
                "完了日時": _date(datetime.now(JST)),
            },
        )
        return {
            "task_id": task["task_id"],
            "status": final_status,
            "user_id": str(task["metadata"].get("line_user_id", "")),
            "message": (f"作業完了: {task['task_id']}\n状態: {final_status}\n「進捗」で結果を確認できます。"),
        }
    except CostLimitError as exc:
        reason = str(exc)[:1500]
        _update_page(
            task["page_id"],
            {
                "状態": _select("blocked"),
                "結果リンク": _rich_text(f"blocked: {reason}"),
                "完了日時": _date(datetime.now(JST)),
            },
        )
        return {
            "task_id": task["task_id"],
            "status": "blocked",
            "user_id": str(task["metadata"].get("line_user_id", "")),
            "message": (f"作業停止: {task['task_id']}\n理由: {reason[:300]}"),
        }
    except Exception as exc:
        reason = str(exc)[:1500]
        _update_page(
            task["page_id"],
            {
                "状態": _select("blocked"),
                "結果リンク": _rich_text(f"blocked: {reason}"),
                "完了日時": _date(datetime.now(JST)),
            },
        )
        return {
            "task_id": task["task_id"],
            "status": "blocked",
            "user_id": str(task["metadata"].get("line_user_id", "")),
            "message": (f"作業停止: {task['task_id']}\n理由: {reason[:300]}"),
        }


def pickup_and_run(limit: int | None = None) -> list[dict[str, str]]:
    """Claim queued tasks in parallel and dispatch draft-only workers."""
    configured = int(os.environ.get("LINE_BRIDGE_PICKUP_LIMIT", "50"))
    max_tasks = min(limit or configured, 100)
    pages = _query_queued(max_tasks)
    if not pages:
        return []
    completed: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_process_single_task, page) for page in pages]
        for future in as_completed(futures):
            result = future.result()
            if result:
                completed.append(result)
    return completed


def build_queue_progress(limit: int = 10) -> str:
    data = _notion_request(
        "POST",
        f"databases/{_queue_db_id()}/query",
        {
            "sorts": [{"property": "作成日時", "direction": "descending"}],
            "page_size": min(limit, 20),
        },
    )
    lines = ["AI作業キュー進捗"]
    for page in data.get("results", []):
        props = page.get("properties", {})
        task_id = _extract_text(props.get("task_id", {}))
        status = _extract_select(props.get("状態", {}))
        assignee = _extract_select(props.get("担当", {}))
        result = _extract_text(props.get("結果リンク", {}))
        line = f"- {task_id} [{status}] {assignee}"
        if status in ("done", "review", "blocked") and result:
            line += f"\n  {result[:300]}"
        lines.append(line)
    review_tasks = get_review_tasks()
    if review_tasks:
        lines.append("")
        for task in review_tasks:
            lines.append(_format_review_task_block(task))
    return "\n".join(lines) if len(lines) > 1 else "AI作業キューは空です。"


def expire_finished(retention_days: int | None = None) -> int:
    days = retention_days or int(os.environ.get("LINE_BRIDGE_RETENTION_DAYS", "30"))
    cutoff = datetime.now(JST) - timedelta(days=max(days, 1))
    data = _notion_request(
        "POST",
        f"databases/{_queue_db_id()}/query",
        {
            "filter": {
                "and": [
                    {
                        "or": [
                            {
                                "property": "状態",
                                "select": {"equals": "done"},
                            },
                            {
                                "property": "状態",
                                "select": {"equals": "blocked"},
                            },
                        ]
                    },
                    {
                        "property": "完了日時",
                        "date": {"before": cutoff.isoformat()},
                    },
                ]
            },
            "page_size": 100,
        },
    )
    count = 0
    for page in data.get("results", []):
        _notion_request("PATCH", f"pages/{page['id']}", {"archived": True})
        count += 1
    return count


def cron_authorized(headers: Any) -> bool:
    expected = os.environ.get("LINE_BRIDGE_CRON_TOKEN", "")
    supplied = headers.get("X-Line-Bridge-Token", "")
    return bool(expected) and supplied == expected


def worker_authorized(headers: Any) -> bool:
    return cron_authorized(headers)


def consume_completion_push_budget() -> bool:
    limit = max(0, min(int(os.environ.get("LINE_BRIDGE_PUSH_MONTHLY_LIMIT", "20")), 99))
    if limit == 0:
        return False
    now = datetime.now(JST)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    data = _notion_request(
        "POST",
        f"databases/{_queue_db_id()}/query",
        {
            "filter": {
                "and": [
                    {
                        "or": [
                            {"property": "状態", "select": {"equals": "done"}},
                            {"property": "状態", "select": {"equals": "review"}},
                            {"property": "状態", "select": {"equals": "blocked"}},
                        ]
                    },
                    {
                        "property": "完了日時",
                        "date": {"on_or_after": month_start.isoformat()},
                    },
                ]
            },
            "page_size": limit + 1,
        },
    )
    return len(data.get("results", [])) <= limit
