# 【Cursor作業指示】タスク1: skill_judge.py CostGuard追加 + max_tokens修正

対象: ses_work/matching_v2/skill_judge.py
優先度: P1
根拠: 週末Opus調査+壁打ち済み。JSONDecodeErrorが現在進行形(char8180)。ledger未被覆。

## 背景
- L138: max_tokens=4000 で出力が途中で切れJSONDecodeErrorが発生中
- L30: usage_tracker.cost_loggerで記録のみ。can_spend事前遮断なし
- 修正方針: max_tokens引上げ + ledger.can_spend被覆（補修案。v3置き換えは用途が別なので不可）

## 修正1: import追加（L30のfrom usage_tracker...の直後）
```python
import sys as _sys
import os as _os
_SES_WORK_DIR = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _SES_WORK_DIR not in _sys.path:
    _sys.path.insert(0, _SES_WORK_DIR)
try:
    from common.ledger import can_spend as _can_spend, record as _ledger_record
    _LEDGER_OK = True
except Exception:
    _LEDGER_OK = False
```

## 修正2: max_tokens 4000→8000（L138）
```python
# Before
max_tokens=4000,
# After
max_tokens=8000,
```

## 修正3: _messages_create内 `max_retries = 5` の直後に事前チェック追加
```python
    if _LEDGER_OK:
        if not _can_spend(2000, 8000, model_name):
            raise RuntimeError("[skill_judge] CostGuard: 日次/月次上限超過")
```

## 修正4: _log_response_cost関数にledger記録を追加（既存のlog_cost呼び出しの直後）
```python
    if _LEDGER_OK:
        try:
            _ledger_record(in_tok, out_tok, model_name, "matching_v2_skill_judge")
        except Exception:
            pass
```
※ in_tok/out_tokは既存のgetattr(usage, "input_tokens", 0)等を使う

## 完了確認
```
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
python -c "import sys; sys.path.insert(0,'.'); from matching_v2.skill_judge import judge_skills; print('OK')"
```


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
