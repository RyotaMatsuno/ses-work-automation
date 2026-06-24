# -*- coding: utf-8 -*-
"""006・007・008を直接実装するスクリプト"""

import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
BRIDGE = os.path.join(SES, "line_webhook", "line_bridge.py")

# ── 006: line_bridge.py に push_or_log 等を追加 ──
content = open(BRIDGE, encoding="utf-8").read()

# _ensure_env_loaded の後に追加（既にあればスキップ）
if "push_or_log" not in content:
    INSERT_AFTER = 'def _ensure_env_loaded() -> None:\n    if os.environ.get("NOTION_API_KEY") or dotenv_values is None:\n        return\n    if not _ENV_PATH.exists():\n        return\n    for key, value in dotenv_values(_ENV_PATH).items():\n        if value and key not in os.environ:\n            os.environ[key] = value'

    NEW_FUNCS = '''

def _line_push_remaining() -> int:
    """今月のLINE push残通数を返す。エラー時は-1。"""
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return -1
    try:
        r_quota = requests.get(
            "https://api.line.me/v2/bot/message/quota",
            headers={"Authorization": f"Bearer {token}"}, timeout=5,
        )
        r_used = requests.get(
            "https://api.line.me/v2/bot/message/quota/consumption",
            headers={"Authorization": f"Bearer {token}"}, timeout=5,
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


def push_or_log(user_id: str, text: str, task_id: str = "") -> str:
    """
    LINE残通数を確認してpushを試みる。
    残0またはpush失敗の場合はNotionキューに記録する。
    戻り値: 'pushed' | 'notion_logged' | 'failed'
    """
    remaining = _line_push_remaining()
    if remaining != 0:
        if _send_line_push_raw(user_id, text):
            return "pushed"
    try:
        now = datetime.now(JST)
        reason = f"LINE push失敗（残{remaining}通）" if remaining == 0 else "LINE push失敗"
        if task_id:
            page = _find_task(task_id)
            if page:
                existing = _extract_text(page.get("properties", {}).get("結果リンク", {}))
                _update_page(page["id"], {"結果リンク": _rich_text(
                    existing + f"\\n[通知未達 {now.strftime('%H:%M')}] {reason}。Claude.aiで確認してください。"
                )})
                return "notion_logged"
        _notion_request("POST", "pages", {"parent": {"database_id": _queue_db_id()}, "properties": {
            "task_id": _title(f"push_fail_{now.strftime('%Y%m%d%H%M%S')}"),
            "受付元": _select("LINE"), "種別": _select("dev"), "優先度": _select("低"),
            "締切": _select("今日中"),
            "入力データ": _rich_text(json.dumps(
                {"text": text, "line_user_id": user_id, "reason": reason}, ensure_ascii=False)),
            "使用許可": _select("draft-only"), "担当": _select("jobz"), "状態": _select("blocked"),
            "結果リンク": _rich_text(f"[通知未達] {reason}\\n内容: {text[:300]}"),
            "人間確認": _select("要"), "作成日時": _date(now),
        }})
        return "notion_logged"
    except Exception:
        return "failed"
'''

    content = content.replace(INSERT_AFTER, INSERT_AFTER + NEW_FUNCS)
    print("006: push_or_log を追加")
else:
    print("006: push_or_log は既存")

# ── 007: handle_router_message を進捗コマンド対応に差し替え ──
OLD_HRM = '''def handle_router_message(
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
    return {"handled": False}'''

NEW_HRM = '''def handle_router_message(
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
        return {"handled": True, "reply": (
            "進捗コマンドは3種類あります:\\n"
            "・作業進捗 → AIキューの作業状況\\n"
            "・案件進捗 → 案件DBの状況（準備中）\\n"
            "・人員進捗 → エンジニアの稼働状況（準備中）"
        )}
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
    return {"handled": False}'''

if OLD_HRM in content:
    content = content.replace(OLD_HRM, NEW_HRM)
    print("007: handle_router_message を差し替え")
else:
    print("007: 差し替え対象が見つかりません（要確認）")

with open(BRIDGE, "w", encoding="utf-8") as f:
    f.write(content)
print("line_bridge.py 書き込み完了")

# ── 動作確認 ──
r = subprocess.run(
    [
        sys.executable,
        "-c",
        "import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work'); "
        "from line_webhook.line_bridge import push_or_log, _line_push_remaining, handle_router_message; "
        "r=handle_router_message('作業進捗','u','m',0); "
        "print('006 OK' if callable(push_or_log) else '006 NG'); "
        "print('007 OK' if r['handled'] else '007 NG')",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=SES,
    timeout=15,
)
print(r.stdout.strip())
if r.stderr:
    print("ERR:", r.stderr[:200])
