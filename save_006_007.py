# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

tasks = {
    "006_line_push_fallback.md": """# 【Cursor作業指示】LINE push残通数フォールバック

対象: ses_work/line_webhook/line_bridge.py / ses_work/gate_checker/gate_check.py
優先度: P1

## タスク1: line_bridge.py に以下3関数を追加（_ensure_env_loaded()の直後）

```python
def _line_push_remaining() -> int:
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return -1
    try:
        r_quota = requests.get("https://api.line.me/v2/bot/message/quota",
                               headers={"Authorization": f"Bearer {token}"}, timeout=5)
        r_used = requests.get("https://api.line.me/v2/bot/message/quota/consumption",
                              headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if r_quota.status_code == 200 and r_used.status_code == 200:
            return max(0, r_quota.json().get("value", 200) - r_used.json().get("totalUsage", 0))
    except Exception:
        pass
    return -1

def _send_line_push_raw(user_id: str, text: str) -> bool:
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return False
    try:
        r = requests.post("https://api.line.me/v2/bot/message/push",
                          headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                          json={"to": user_id, "messages": [{"type": "text", "text": text}]},
                          timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def push_or_log(user_id: str, text: str, task_id: str = "") -> str:
    remaining = _line_push_remaining()
    if remaining != 0:
        if _send_line_push_raw(user_id, text):
            return "pushed"
    # push失敗 → Notionに記録
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
            "入力データ": _rich_text(json.dumps({"text": text, "line_user_id": user_id, "reason": reason}, ensure_ascii=False)),
            "使用許可": _select("draft-only"), "担当": _select("jobz"), "状態": _select("blocked"),
            "結果リンク": _rich_text(f"[通知未達] {reason}\\n内容: {text[:300]}"),
            "人間確認": _select("要"), "作成日時": _date(now),
        }})
        return "notion_logged"
    except Exception:
        return "failed"
```

## タスク2: gate_check.py の send_line_notification() 内、pushの直前に追加

```python
    # LINE残通数確認
    try:
        import requests as _req
        r_used = _req.get("https://api.line.me/v2/bot/message/quota/consumption",
                          headers={"Authorization": f"Bearer {token}"}, timeout=5)
        r_quota = _req.get("https://api.line.me/v2/bot/message/quota",
                           headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if r_used.status_code == 200 and r_quota.status_code == 200:
            remaining = r_quota.json().get("value", 200) - r_used.json().get("totalUsage", 0)
            if remaining <= 0:
                logger.warning("LINE push残0通のためスキップ。Claude.aiで確認 phase=%s", phase)
                return False
    except Exception:
        pass
```

HTTPError 429 のハンドリングを変更（raiseしない）:
```python
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                logger.warning("LINE push 429（月次上限）。Claude.aiで確認 phase=%s", phase)
                return False
            logger.error("LINE通知失敗: status=%s", exc.code)
```

## 完了確認
```python
import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work')
from line_webhook.line_bridge import push_or_log, _line_push_remaining
print(f"残通数: {_line_push_remaining()}通 / push_or_log: OK")
```
完了後に「LINE通知リファクタ完了」とClaude.aiに報告すること。
""",
    "007_line_progress_commands.md": """# 【Cursor作業指示】進捗コマンド3分割 Step1

対象: ses_work/line_webhook/line_bridge.py
優先度: P0（本番バグ: 「進捗」でマッチング結果が返る）

## handle_router_message() を以下に完全差し替え

```python
def handle_router_message(
    text: str,
    user_id: str,
    message_id: str,
    event_timestamp_ms: int,
) -> dict[str, Any]:
    stripped = text.strip()

    # 完全一致コマンド（最優先）
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

    # 既存処理（変更なし）
    if stripped.startswith(("/run ", "/bg ")) or stripped in ("/log", "/health"):
        return {"handled": False}
    result = route_line_message(
        text=stripped, user_id=user_id, message_id=message_id,
        event_timestamp_ms=event_timestamp_ms, reply_token="",
    )
    if result.get("action") == "reply":
        return {"handled": True, "reply": result["text"]}
    return {"handled": False}
```

## 完了確認
```python
import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work')
from line_webhook.line_bridge import handle_router_message
assert handle_router_message("作業進捗","u","m",0)["handled"]
assert "3種類" in handle_router_message("進捗","u","m",0)["reply"]
assert not handle_router_message("案件進捗どう","u","m",0)["handled"]
print("全テスト合格")
```

完了後に「進捗コマンド改修完了」とClaude.aiに報告すること。
その後 Cloud Run デプロイ:
```bash
gcloud run deploy line-webhook --source ses_work/line_webhook --region asia-northeast1 --update-env-vars DUMMY=1
```
""",
}

for filename, content in tasks.items():
    path = os.path.join(PENDING, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"保存: {filename}")

print(f"\npending_tasks: {sorted(os.listdir(PENDING))}")
