# -*- coding: utf-8 -*-
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"

task = r"""# 【Cursor作業指示】LINE上限前提の通知設計リファクタ

対象: ses_work/line_webhook/line_bridge.py / ses_work/gate_checker/gate_check.py
優先度: P1
根拠: 2026-06-15に200/200通到達確認。毎月末に同じ問題が再発する。

## 設計方針（ジョブズ確定）

LINEをpush送信の「必須経路」から「オプション経路」に降格する。
push失敗時は Notion AI作業キューに書くだけでOK。
松野は「作業進捗」とLINEに打てばNotion経由で状態が返ってくる（reply=1通消費）。
push失敗=作業消失ではなく、Notionが唯一のSSoT。

```
現状:  処理完了 → LINE push → (200通超でロスト)
新設計: 処理完了 → Notion更新(必須) → LINE push(残通数があれば) → 残0でもNotionで確認可
```

---

## タスク1: line_bridge.py に push_or_log() を実装

### 1-1. push残通数をチェックする関数を追加

`_ensure_env_loaded()` の直後あたりに追加:

```python
def _line_push_remaining() -> int:
    \"\"\"今月のLINE push残通数を返す。エラー時は0を返す。\"\"\"
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return 0
    try:
        import requests as _req
        r_quota = _req.get(
            "https://api.line.me/v2/bot/message/quota",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        r_used = _req.get(
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
    return 0


def _send_line_push(user_id: str, text: str) -> bool:
    \"\"\"LINE push送信。成功したらTrue、失敗（残0含む）はFalse。\"\"\"
    _ensure_env_loaded()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        return False
    try:
        import requests as _req
        r = _req.post(
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
    LINE pushを試みる。失敗した場合はNotionキューに記録して
    'Claude.aiで確認を' というメッセージを返す。
    戻り値: 'pushed' | 'notion_logged' | 'failed'
    \"\"\"
    remaining = _line_push_remaining()
    if remaining > 0:
        success = _send_line_push(user_id, text)
        if success:
            return "pushed"

    # push失敗 → Notionキューに通知レコードを積む
    try:
        now = datetime.now(JST)
        metadata = {
            "text": text,
            "line_user_id": user_id,
            "push_failed": True,
            "reason": f"LINE push失敗（残{remaining}通）",
        }
        # タスクIDがあれば既存レコードのresult_linkを更新
        if task_id:
            page = _find_task(task_id)
            if page:
                existing = _extract_text(page.get("properties", {}).get("結果リンク", {}))
                _update_page(page["id"], {
                    "結果リンク": _rich_text(
                        existing + f"\n[通知未達 {now.strftime('%H:%M')}] LINE上限到達。Claude.aiで確認してください。"
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
                "入力データ": _rich_text(json.dumps(metadata, ensure_ascii=False)),
                "使用許可": _select("draft-only"),
                "担当": _select("jobz"),
                "状態": _select("blocked"),
                "結果リンク": _rich_text(
                    f"[通知未達] LINE上限到達。内容: {text[:300]}"
                ),
                "人間確認": _select("要"),
                "作成日時": _date(now),
            }
        })
        return "notion_logged"
    except Exception:
        return "failed"
```

### 1-2. _process_single_task() の完了通知を push_or_log() に変更

`_process_single_task()` 内の完了/blocked時の戻り値 `message` を使って
Cloud Run側 (main.py/app.py) がpushを送っているはずなので、
そちらでも push_or_log() を使うよう変更する。

もしline_bridge.py内でpush呼び出しがあれば全て push_or_log() に置き換える。

---

## タスク2: gate_check.py の LINE通知を push_or_log() 経由に変更

**ファイル**: `ses_work/gate_checker/gate_check.py`

`send_line_notification()` 関数を以下に差し替え:

```python
def send_line_notification(
    phase: str, target: str, reason: str, gpt_summary: str, is_ng: bool, env: dict[str, str]
) -> bool:
    token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = env.get("MATSUNO_USER_ID") or env.get("MATSUNO_LINE_USER_ID", "")
    if not token or not user_id:
        logger.warning("LINE通知スキップ: token=%s user_id=%s", bool(token), bool(user_id))
        return False

    summary = gpt_summary.replace("\n", " ").strip()
    if len(summary) > 300:
        summary = summary[:297] + "..."
    template = NOTIFY_TEMPLATE_NG if is_ng else NOTIFY_TEMPLATE
    message = template.format(phase=phase, target=target, reason=reason, gpt_summary=summary)

    # LINE残通数確認
    try:
        import requests as _req
        r_used = _req.get(
            "https://api.line.me/v2/bot/message/quota/consumption",
            headers={"Authorization": f"Bearer {token}"}, timeout=5
        )
        r_quota = _req.get(
            "https://api.line.me/v2/bot/message/quota",
            headers={"Authorization": f"Bearer {token}"}, timeout=5
        )
        if r_used.status_code == 200 and r_quota.status_code == 200:
            remaining = r_quota.json().get("value", 200) - r_used.json().get("totalUsage", 0)
            if remaining <= 0:
                # 残0通 → ログのみ（Claude.aiチャットで確認）
                logger.warning(
                    "LINE push残0通のためスキップ。Claude.aiで確認してください。"
                    " phase=%s target=%s verdict=%s",
                    phase, target, "NG" if is_ng else "GO"
                )
                return False
    except Exception:
        pass

    # push実行
    body = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": message}]},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            logger.info("LINE通知送信完了: status=%s", response.status)
            return True
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 429:
            logger.warning("LINE push 429（月次上限到達）。Claude.aiで確認してください。 phase=%s", phase)
        else:
            logger.error("LINE通知失敗: status=%s body=%s", exc.code, detail)
    except Exception as exc:
        logger.error("LINE通知失敗: %s", exc)
    return False
```

---

## タスク3: 「作業進捗」コマンドの動作確認とNotion進捗URLをLINE replyで返す

**目的**: push残0でもLINEの「作業進捗」コマンドはreply（1通消費）で返せる。
reply は push と異なりカウントされない（または消費が異なる）。
Notion進捗URLを毎回付与することで、松野がブラウザで直接確認できる。

`build_queue_progress()` の戻り値の末尾に追加:
```python
    # Notion進捗URLを付与
    notion_url = f"https://www.notion.so/{_queue_db_id().replace('-','')}"
    lines.append(f"\n📋 詳細: {notion_url}")
    # LINE残通数も表示
    # ※ここでのLINE API呼び出しはreplyハンドラ内なのでカウントなし
    lines.append("（push上限到達中はClaude.aiまたは上記NotionURLで確認）")
```

---

## 完了確認

```python
# line_bridge.py の push_or_log が使えるか確認
import sys; sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work')
from line_webhook.line_bridge import push_or_log, _line_push_remaining
remaining = _line_push_remaining()
print(f"LINE残通数: {remaining}通")
print("push_or_log import OK")
```

```
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
python gate_checker/gate_check.py --phase requirements --file gate_checker/SPEC.md
```
429エラーが出ずにgate_checkerが完了すること（push失敗のログが出ても処理続行すること）。

完了後に「LINE通知リファクタ完了」とClaude.aiに報告すること。
"""

path = os.path.join(PENDING, "006_line_push_fallback.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(task)
print("保存: 006_line_push_fallback.md")
print(f"現在のpending_tasks: {os.listdir(PENDING)}")
