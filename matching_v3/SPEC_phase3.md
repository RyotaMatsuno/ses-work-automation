# Phase3 SPEC: 各コンポーネントへのLedger接続

## A. matching_v3/structurer.py の変更

### 変更点
1. ファイル先頭のimportに以下を追加:
```python
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))
from common.ledger import can_spend as _ledger_can_spend, record as _ledger_record
```

2. `structure()` 関数内の変更:
   - `if not cost_guard.can_call(est_input_tokens, est_output_tokens):` の前に追加:
     ```python
     if not _ledger_can_spend(est_input_tokens, est_output_tokens, DEFAULT_STRUCTURER_MODEL):
         logger.warning("Global cost limit reached, skipping")
         raise RuntimeError("global cost limit reached")
     ```
   - `cost_guard.record_cost(...)` の呼び出しの後に追加:
     ```python
     _ledger_record(input_tokens, output_tokens, model, "matching_v3")
     ```

## B. matching_v3/cost_guard.py の変更

`can_call()` メソッドの先頭に追加:
```python
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))
try:
    from common.ledger import can_spend as _global_can_spend
    def can_call(self, est_input_tokens: int, est_output_tokens: int) -> bool:
        # グローバル上限を先にチェック
        from config import DEFAULT_STRUCTURER_MODEL
        if not _global_can_spend(est_input_tokens, est_output_tokens, DEFAULT_STRUCTURER_MODEL):
            return False
        # 既存ローカル上限チェック（バックアップとして残す）
        daily = self._get_daily_stats()
        if int(daily["api_calls"]) >= self.DAILY_CALL_LIMIT:
            return False
        est_cost = self._estimate_cost(est_input_tokens, est_output_tokens)
        if float(daily["total_cost_usd"]) + est_cost > self.DAILY_COST_LIMIT_USD:
            return False
        if self._get_monthly_cost() >= self.MONTHLY_STOP_USD:
            return False
        return True
except ImportError:
    pass  # fallback: 既存ロジックをそのまま使う
```
※注意: メソッドのインデント・構造を崩さないこと。既存のメソッドを上書きする形で実装。

## C. outlook/outlook_to_notion.py の変更

1. `import` セクションに以下を追加（ファイル先頭付近）:
```python
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
try:
    from common.ledger import can_spend as _ledger_can_spend, record as _ledger_record
    _LEDGER_OK = True
except ImportError:
    _LEDGER_OK = False
```

2. モデル定数を変更:
   - `"claude-sonnet-4-20250514"` → `"claude-haiku-4-5-20251001"` に変更（全箇所）

3. Anthropic API呼び出し箇所の前後に追加:
   - 呼び出し前: `if _LEDGER_OK and not _ledger_can_spend(1500, 300, "claude-haiku-4-5-20251001"): return ""`
   - 呼び出し後（成功時）: `if _LEDGER_OK: _ledger_record(usage.get("input_tokens",0), usage.get("output_tokens",0), "claude-haiku-4-5-20251001", "outlook")`

## D. mail_attachment_importer/ai_extractor.py の変更

1. `import` セクションに追加:
```python
import sys as _sys, os as _os
_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".."))
try:
    from common.ledger import can_spend as _ledger_can_spend, record as _ledger_record
    _LEDGER_OK = True
except ImportError:
    _LEDGER_OK = False
```

2. client.messages.create() の前後に追加（全呼び出し箇所）:
   - 前: `if _LEDGER_OK and not _ledger_can_spend(500, 100, "claude-haiku-4-5-20251001"): return {}  # or return []`
   - 後（成功時）: usageを取得して `if _LEDGER_OK: _ledger_record(usage.input_tokens, usage.output_tokens, "claude-haiku-4-5-20251001", "importer")`

## 完了確認
- matching_v3/structurer.py に `_ledger_record` の呼び出しがある
- outlook/outlook_to_notion.py のモデルが haiku-4-5-20251001 になっている
- ai_extractor.py に `_ledger_can_spend` の呼び出しがある
