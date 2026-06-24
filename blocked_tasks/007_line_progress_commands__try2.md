# 【Cursor作業指示】進捗コマンド3分割 Step1

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
            "進捗コマンドは3種類あります:\n"
            "・作業進捗 → AIキューの作業状況\n"
            "・案件進捗 → 案件DBの状況（準備中）\n"
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
import sys; sys.path.insert(0, r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work')
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


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
