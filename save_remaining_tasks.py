# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

tasks = {
    "006_line_push_fallback.md": """# 【Cursor作業指示】LINE push残通数フォールバック設計

対象: ses_work/line_webhook/line_bridge.py / ses_work/gate_checker/gate_check.py
優先度: P1
根拠: 2026-06-15に200/200通到達確認。毎月末に同じ問題が再発する。上限前提の設計に変更する。

## 設計方針
LINEをpush送信の「必須経路」から「オプション経路」に降格する。
push失敗時はNotionに書くだけでOK。
松野は「作業進捗」とLINEに打てばreply（カウントなし）で状態が返る。

---

## タスク1: line_bridge.py に _line_push_remaining() と push_or_log() を追加

_ensure_env_loaded() の直後に以下を追加:

```python
def _line_push_remaining() -> int:
    \"\"\"今月のLINE push残通数を返す。エラー時は-1を返す。\"\"\"
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
            limit = r_quota.json().get("value", 200)
            used = r_used.json().get("totalUsage", 0)
            return max(0, limit - used)
    except Exception:
        pass
    return -1


def _send_line_push_raw(user_id: str, text: str) -> bool:
    \"\"\"LINE push送信。成功したらTrue。\"\"\"
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return False
    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"to": user_id, "messages": [{"type": "text", "text": text}]},
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def push_or_log(user_id: str, text: str, task_id: str = "") -> str:
    \"\"\"
    LINE残通数を確認してpushを試みる。
    残0またはpush失敗の場合はNotionキューに記録する。
    戻り値: 'pushed' | 'notion_logged' | 'failed'
    \"\"\"
    remaining = _line_push_remaining()
    if remaining != 0:  # -1(不明)または残あり → pushを試みる
        if _send_line_push_raw(user_id, text):
            return "pushed"

    # push失敗 → Notionキューに通知レコードを積む
    try:
        now = datetime.now(JST)
        reason = f"LINE push失敗（残{remaining}通）" if remaining == 0 else "LINE push失敗"
        # 既存タスクのresult_linkに追記
        if task_id:
            page = _find_task(task_id)
            if page:
                existing = _extract_text(page.get("properties", {}).get("結果リンク", {}))
                _update_page(page["id"], {
                    "結果リンク": _rich_text(
                        existing + f"\\n[通知未達 {now.strftime('%H:%M')}] {reason}。Claude.aiで確認してください。"
                    )
                })
                return "notion_logged"
        # 新規レコード
        _notion_request("POST", "pages", {
            "parent": {"database_id": _queue_db_id()},
            "properties": {
                "task_id": _title(f"push_fail_{now.strftime('%Y%m%d%H%M%S')}"),
                "受付元": _select("LINE"),
                "種別": _select("dev"),
                "優先度": _select("低"),
                "締切": _select("今日中"),
                "入力データ": _rich_text(json.dumps({"text": text, "line_user_id": user_id, "reason": reason}, ensure_ascii=False)),
                "使用許可": _select("draft-only"),
                "担当": _select("jobz"),
                "状態": _select("blocked"),
                "結果リンク": _rich_text(f"[通知未達] {reason}\\n内容: {text[:300]}"),
                "人間確認": _select("要"),
                "作成日時": _date(now),
            }
        })
        return "notion_logged"
    except Exception:
        return "failed"
```

---

## タスク2: gate_check.py の send_line_notification() を残通数チェック付きに修正

send_line_notification() 内、pushを実行する urllib.request.Request の直前に以下を追加:

```python
    # LINE残通数確認（残0なら送らずログのみ）
    try:
        import requests as _req
        r_used = _req.get("https://api.line.me/v2/bot/message/quota/consumption",
                          headers={"Authorization": f"Bearer {token}"}, timeout=5)
        r_quota = _req.get("https://api.line.me/v2/bot/message/quota",
                           headers={"Authorization": f"Bearer {token}"}, timeout=5)
        if r_used.status_code == 200 and r_quota.status_code == 200:
            remaining = r_quota.json().get("value", 200) - r_used.json().get("totalUsage", 0)
            if remaining <= 0:
                logger.warning(
                    "LINE push残0通のためスキップ。Claude.aiで確認してください。"
                    " phase=%s target=%s", phase, target
                )
                return False
    except Exception:
        pass
```

また既存の HTTPError 429 のハンドリングを以下に変更（エラーにせずwarningで続行）:
```python
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                logger.warning("LINE push 429（月次上限到達）。Claude.aiで確認してください。 phase=%s", phase)
                return False  # raiseしない
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            logger.error("LINE通知失敗: status=%s body=%s", exc.code, detail)
```

---

## 完了確認

```python
import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work')
from line_webhook.line_bridge import push_or_log, _line_push_remaining
remaining = _line_push_remaining()
print(f"LINE残通数: {remaining}通")
print("push_or_log import OK")
```

完了後に「LINE通知リファクタ完了」とClaude.aiに報告すること。
""",
    "007_line_progress_commands.md": """# 【Cursor作業指示】進捗コマンド3分割 Step1 + Cloud Runデプロイ

対象: ses_work/line_webhook/line_bridge.py
優先度: P0（現在「進捗」でマッチング結果が返ってくるバグが本番稼働中）
根拠: 引き継ぎメッセージ 2026-06-15確定方針。松野承認済み。

## 背景
- 現状「進捗」を送るとmatching_v3のマッチング結果と衝突する
- 完全一致コマンドに変更して誤検知をゼロにする
- Step1: 「作業進捗」のみ実装。Step2・3は別途DB設計後

## 修正: handle_router_message() を以下に差し替え

```python
def handle_router_message(
    text: str,
    user_id: str,
    message_id: str,
    event_timestamp_ms: int,
) -> dict[str, Any]:
    stripped = text.strip()

    # ── 完全一致コマンド（最優先・マッチング判定より前に処理）──
    if stripped == "作業進捗":
        progress = build_queue_progress(limit=10)
        return {"handled": True, "reply": progress}

    if stripped == "進捗":
        guide = (
            "進捗コマンドは3種類あります:\\n"
            "・作業進捗 → AIキューの作業状況\\n"
            "・案件進捗 → 案件DBの状況（準備中）\\n"
            "・人員進捗 → エンジニアの稼働状況（準備中）"
        )
        return {"handled": True, "reply": guide}

    if stripped == "案件進捗":
        return {"handled": True, "reply": "案件進捗機能は準備中です。\\nお急ぎの場合はNotion案件DBを直接ご確認ください。"}

    if stripped == "人員進捗":
        return {"handled": True, "reply": "人員進捗機能は準備中です。\\nお急ぎの場合はNotionエンジニアDBを直接ご確認ください。"}

    # ── 以降は既存のルーティング処理（変更なし）──
    if (
        stripped.startswith(("/run ", "/bg "))
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
```

## 完了確認（ローカル）

```python
import sys; sys.path.insert(0, r'C:\\Users\\ma_py\\OneDrive\\デスクトップ\\ses_work')
from line_webhook.line_bridge import handle_router_message

r = handle_router_message("作業進捗", "test_user", "msg1", 0)
assert r["handled"] == True, "作業進捗がhandledされていない"
print("作業進捗 OK:", r["reply"][:50])

r2 = handle_router_message("進捗", "test_user", "msg2", 0)
assert r2["handled"] == True
assert "3種類" in r2["reply"], "ガイドメッセージが出ていない"
print("進捗ガイド OK")

r3 = handle_router_message("案件の進捗どう", "test_user", "msg3", 0)
assert r3["handled"] == False, "部分一致でhandledされてはいけない"
print("部分一致スルー OK")

print("全テスト合格")
```

## Cloud Runデプロイ（確認後に実行）

```bash
gcloud run deploy line-webhook --source ses_work/line_webhook --region asia-northeast1 --update-env-vars DUMMY=1
```

※ --update-env-vars を使う（--set-env-vars は既存変数を消すので禁止）
デプロイ後にLINEで「作業進捗」と送って動作確認。

完了後に「進捗コマンド改修完了」とClaude.aiに報告すること。
""",
}

# 既存ファイルを確認してから保存
existing = os.listdir(PENDING)
print(f"既存pending_tasks: {existing}")

for filename, content in tasks.items():
    path = os.path.join(PENDING, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"保存: {filename}")

print(f"\n完了。pending_tasks: {sorted(os.listdir(PENDING))}")
