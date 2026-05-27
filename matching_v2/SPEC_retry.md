# SPEC_retry.md - skill_judge.py に529リトライロジック追加

## 目的
Claude API過負荷（529 OverloadedError）が発生した場合に自動リトライする。

## 対象ファイル
matching_v2/skill_judge.py

## 修正箇所: _messages_create() 関数

現在は1回呼んで終わり。以下のリトライロジックを追加する。

```python
import time

def _messages_create(client, model_name, prompt):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model=model_name,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
        except Exception as e:
            err_str = str(e)
            if "529" in err_str or "overloaded" in err_str.lower():
                wait = 10 * (attempt + 1)  # 10, 20, 30, 40, 50秒
                print(f"[skill_judge] API過負荷(529) attempt={attempt+1}/{max_retries} wait={wait}s")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Claude API 529 over max_retries")
```

## 確認
修正後に python -c "import matching_v2.skill_judge; print('import OK')" を実行。

## TASKS_retry.md
- [ ] import time が先頭にあることを確認（なければ追加）
- [ ] _messages_create() をリトライロジック付きに書き換え
- [ ] import確認テスト
