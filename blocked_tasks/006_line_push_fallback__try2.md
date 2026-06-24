# 【Cursor作業指示】LINE push残通数フォールバック

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
                    existing + f"\n[通知未達 {now.strftime('%H:%M')}] {reason}。Claude.aiで確認してください。"
                )})
                return "notion_logged"
        _notion_request("POST", "pages", {"parent": {"database_id": _queue_db_id()}, "properties": {
            "task_id": _title(f"push_fail_{now.strftime('%Y%m%d%H%M%S')}"),
            "受付元": _select("LINE"), "種別": _select("dev"), "優先度": _select("低"),
            "締切": _select("今日中"),
            "入力データ": _rich_text(json.dumps({"text": text, "line_user_id": user_id, "reason": reason}, ensure_ascii=False)),
            "使用許可": _select("draft-only"), "担当": _select("jobz"), "状態": _select("blocked"),
            "結果リンク": _rich_text(f"[通知未達] {reason}\n内容: {text[:300]}"),
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
import sys; sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work')
from line_webhook.line_bridge import push_or_log, _line_push_remaining
print(f"残通数: {_line_push_remaining()}通 / push_or_log: OK")
```
完了後に「LINE通知リファクタ完了」とClaude.aiに報告すること。


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
