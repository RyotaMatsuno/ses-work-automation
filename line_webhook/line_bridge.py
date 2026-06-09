# -*- coding: utf-8 -*-
"""LINE instruction router, Notion work queue, and draft-only workers."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
NOTION_VERSION = "2022-06-28"
MATSUNO_USER_ID = os.environ.get(
    "MATSUNO_LINE_USER_ID", "Ue3508b43b84991f5a68281da5bf4cf39"
)
MODEL = os.environ.get("LINE_BRIDGE_MODEL", "claude-haiku-4-5-20251001")
CLAUDE_MODEL = MODEL

_CONFIRMATIONS: dict[str, dict[str, Any]] = {}
_CONFIRMATION_TTL_SECONDS = 600
_PICKUP_LOCK = threading.Lock()


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
    "送信", "メールして", "請求", "確定", "契約", "本番", "更新",
    "登録", "freee", "入金消込",
)
SALES_HEAVY_WORDS = (
    "重作業", "深掘り", "提案文まで", "提案文作成", "評価表",
    "意向確認文", "面談調整",
)
ACCOUNTING_WORDS = (
    "請求", "入金", "契約マスター", "試算", "節税", "法人化",
    "払出", "freee",
)
DEVELOPMENT_WORDS = (
    "costguard", "cursor", "codex", "claude code", "開発", "コード",
    "バグ", "修正して", "実装して",
)
IMMEDIATE_WORDS = (
    "今日の案件", "この人どう", "マッチング", "案件一覧", "人材一覧",
    "進捗", "案件", "人材", "スキルシート", "この人",
)


def _queue_db_id() -> str:
    return os.environ.get("NOTION_AI_QUEUE_DB_ID", "")


class CostGuard:
    """Cost guard with kill switch and daily/monthly/batch limits."""

    _lock = threading.Lock()
    _state_path = Path(
        os.environ.get("LINE_BRIDGE_COST_STATE", "/tmp/line_bridge_cost.json")
    )
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
        cls._state_path.write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )

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
        batch_limit = int(os.environ.get("LINE_BRIDGE_BATCH_LLM_LIMIT", "3"))
        with cls._lock:
            if cls._batch_active and cls._batch_calls >= batch_limit:
                raise RuntimeError("CostGuard: batch limit exceeded")
            state = cls._load()
            if float(state["daily_usd"]) + estimated > daily_limit:
                raise RuntimeError("CostGuard: daily limit exceeded")
            if float(state["monthly_usd"]) + estimated > monthly_limit:
                raise RuntimeError("CostGuard: monthly limit exceeded")
            state["daily_usd"] = round(float(state["daily_usd"]) + estimated, 8)
            state["monthly_usd"] = round(
                float(state["monthly_usd"]) + estimated, 8
            )
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
            return (
                float(state["daily_usd"]) < daily_limit
                and float(state["monthly_usd"]) < monthly_limit
            )

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
        cost = (
            max(input_tokens, 0) * rates[0]
            + max(output_tokens, 0) * rates[1]
        ) / 1_000_000
        with cls._lock:
            state = cls._load()
            state["daily_usd"] = round(float(state["daily_usd"]) + cost, 8)
            state["monthly_usd"] = round(
                float(state["monthly_usd"]) + cost, 8
            )
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


def _notion_request(
    method: str, path: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    response = requests.request(
        method,
        f"https://api.notion.com/v1/{path}",
        headers=_notion_headers(),
        json=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Notion API {response.status_code}: {response.text[:300]}"
        )
    return response.json()


def _title(value: str) -> dict[str, Any]:
    return {"title": [{"text": {"content": value[:2000]}}]}


def _rich_text(value: str) -> dict[str, Any]:
    chunks = [
        value[index:index + 2000]
        for index in range(0, min(len(value), 20000), 2000)
    ]
    return {
        "rich_text": [{"text": {"content": chunk}} for chunk in chunks]
    }


def _select(value: str) -> dict[str, Any]:
    return {"select": {"name": value}}


def _date(value: datetime) -> dict[str, Any]:
    return {"date": {"start": value.isoformat()}}


def _extract_text(prop: dict[str, Any]) -> str:
    values = prop.get("title") or prop.get("rich_text") or []
    return "".join(item.get("plain_text", "") for item in values)


def _extract_select(prop: dict[str, Any]) -> str:
    return (prop.get("select") or {}).get("name", "")


def classify_route(text: str) -> dict[str, str]:
    normalized = text.strip().lower()
    if normalized.startswith("/"):
        return {
            "route": "immediate",
            "kind": "matching",
            "assignee": "matching_v3",
            "human_confirmation": "不要",
        }
    confirmation = (
        "要"
        if any(word.lower() in normalized for word in SENSITIVE_WORDS)
        else "不要"
    )
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


def _route_from_confirmation(
    choice: str, original: str
) -> dict[str, str] | None:
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
    timestamp_min = datetime.fromtimestamp(
        event_timestamp_ms / 1000, tz=JST
    ).strftime("%Y%m%d%H%M")
    source = f"{user_id}{message_id}{timestamp_min}".encode("utf-8")
    return hashlib.sha256(source).hexdigest()[:16]


def _find_task(task_id: str) -> dict[str, Any] | None:
    db_id = _queue_db_id()
    data = _notion_request(
        "POST",
        f"databases/{db_id}/query",
        {
            "filter": {
                "property": "task_id",
                "title": {"equals": task_id},
            },
            "page_size": 1,
        },
    )
    results = data.get("results", [])
    return results[0] if results else None


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
    properties = {
        "task_id": _title(task_id),
        "受付元": _select("LINE"),
        "種別": _select(route["kind"]),
        "優先度": _select("中"),
        "締切": _select("今日中"),
        "入力データ": _rich_text(json.dumps(metadata, ensure_ascii=False)),
        "使用許可": _select("draft-only"),
        "担当": _select(route["assignee"]),
        "状態": _select("queued"),
        "コスト見込み": {"number": 0.01},
        "結果リンク": _rich_text(""),
        "人間確認": _select(route["human_confirmation"]),
        "作成日時": _date(now),
    }
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
            "text": _enqueue_reply(created, task_id, route["assignee"]),
        }

    route = classify_route(text)
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
            "text": (
                "種別を1つ選んで返信してください。\n"
                "1 営業重作業 / 2 経理 / 3 開発 / 4 即時マッチング"
            ),
        }
    created, task_id = enqueue_task(
        text, route, user_id, message_id, event_timestamp_ms, reply_token
    )
    return {
        "action": "reply",
        "text": _enqueue_reply(created, task_id, route["assignee"]),
    }


def handle_router_message(
    text: str,
    user_id: str,
    message_id: str,
    event_timestamp_ms: int,
) -> dict[str, Any]:
    """Compatibility adapter used by the existing webhook integration."""
    stripped = text.strip()
    if (
        stripped in ("進捗", "キュー進捗", "作業進捗")
        or stripped.startswith(("/run ", "/bg "))
        or stripped in ("/log", "/health")
    ):
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


def _enqueue_reply(created: bool, task_id: str, assignee: str) -> str:
    if not created:
        return f"既にキュー登録済みです。\ntask_id: {task_id}"
    return (
        f"作業キューに登録しました。\ntask_id: {task_id}\n担当: {assignee}"
    )


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


def _update_page(
    page_id: str, properties: dict[str, Any]
) -> dict[str, Any]:
    return _notion_request(
        "PATCH", f"pages/{page_id}", {"properties": properties}
    )


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
    system, user = _worker_prompt(
        task["assignee"], str(task["metadata"].get("text", ""))
    )
    result = guarded_anthropic_call(
        system,
        user,
        max_tokens=1200,
        caller=f"line_bridge_{task['assignee']}",
    )
    _validate_draft(result)
    return result


def pickup_and_run(limit: int | None = None) -> list[dict[str, str]]:
    """Claim queued tasks serially and dispatch draft-only workers."""
    configured = int(os.environ.get("LINE_BRIDGE_PICKUP_LIMIT", "3"))
    max_tasks = min(limit or configured, configured, 10)
    completed: list[dict[str, str]] = []
    if not _PICKUP_LOCK.acquire(blocking=False):
        return completed
    CostGuard.begin_batch()
    try:
        for page in _query_queued(max_tasks):
            task = _task_payload(page)
            try:
                _update_page(task["page_id"], {"状態": _select("running")})
                latest = _notion_request("GET", f"pages/{task['page_id']}")
                status = _extract_select(
                    latest.get("properties", {}).get("状態", {})
                )
                if status != "running":
                    continue
                result = _run_worker(task)
                final_status = (
                    "review"
                    if task["human_confirmation"] == "要"
                    else "done"
                )
                _update_page(
                    task["page_id"],
                    {
                        "状態": _select(final_status),
                        "結果リンク": _rich_text(result),
                        "完了日時": _date(datetime.now(JST)),
                    },
                )
                completed.append(
                    {
                        "task_id": task["task_id"],
                        "status": final_status,
                        "user_id": str(
                            task["metadata"].get("line_user_id", "")
                        ),
                        "message": (
                            f"作業完了: {task['task_id']}\n"
                            f"状態: {final_status}\n"
                            "「進捗」で結果を確認できます。"
                        ),
                    }
                )
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
                completed.append(
                    {
                        "task_id": task["task_id"],
                        "status": "blocked",
                        "user_id": str(
                            task["metadata"].get("line_user_id", "")
                        ),
                        "message": (
                            f"作業停止: {task['task_id']}\n理由: {reason[:300]}"
                        ),
                    }
                )
    finally:
        CostGuard.end_batch()
        _PICKUP_LOCK.release()
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
    return "\n".join(lines) if len(lines) > 1 else "AI作業キューは空です。"


def expire_finished(retention_days: int | None = None) -> int:
    days = retention_days or int(
        os.environ.get("LINE_BRIDGE_RETENTION_DAYS", "30")
    )
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
    limit = max(
        0, min(int(os.environ.get("LINE_BRIDGE_PUSH_MONTHLY_LIMIT", "20")), 99)
    )
    if limit == 0:
        return False
    now = datetime.now(JST)
    month_start = now.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
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
