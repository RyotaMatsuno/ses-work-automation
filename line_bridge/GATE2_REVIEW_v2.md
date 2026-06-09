# GATE2 CODE REVIEW v2 (GPT-4o full code)

確認ポイントについての実装確認を行います。

### A) task_id重複検知
- **実装確認: OK**
  - `_task_id()`関数にSHA256ロジックが存在します。
    ```python
    def _task_id(user_id: str, message_id: str, event_timestamp_ms: int) -> str:
        timestamp_min = datetime.fromtimestamp(
            event_timestamp_ms / 1000, tz=JST
        ).strftime("%Y%m%d%H%M")
        source = f"{user_id}{message_id}{timestamp_min}".encode("utf-8")
        return hashlib.sha256(source).hexdigest()[:16]
    ```
  - `_find_task()`で重複チェックを行っています。
    ```python
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
    ```

### B) LINE push 200通節約
- **実装確認: OK**
  - `consume_completion_push_budget()`関数が存在し、月次カウントを行っています。
    ```python
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
    ```

### C) 曖昧判定1往復打ち切り
- **実装確認: OK**
  - `_CONFIRMATIONS`ポップ後に再確認しない実装になっています。
    ```python
    if pending:
        _CONFIRMATIONS.pop(user_id, None)
        route = _route_from_confirmation(text, str(pending["text"]))
        if not route:
            return {
                "action": "reply",
                "text": "判定できないためキュー未登録です。",
            }
    ```

### D) ジラード/渋沢がdraft-only
- **実装確認: OK**
  - `_validate_draft()`で「送信しました/確定しました」などの実行宣言を検知しています。
    ```python
    def _validate_draft(result: str) -> None:
        if not result.strip():
            raise RuntimeError("worker returned an empty draft")
        prohibited = ("送信しました", "確定しました", "更新しました", "登録しました")
        if any(word in result for word in prohibited):
            raise RuntimeError("draft validation failed: execution claim detected")
    ```

### E) CostGuard被覆
- **実装確認: OK**
  - `guarded_anthropic_call()`に`reserve()`呼び出しがあります。
    ```python
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
        ...
    ```

【判定: GO】
