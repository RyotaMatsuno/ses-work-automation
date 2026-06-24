# 【Cursor作業指示】タスク2: agreement_checker.py CostGuard追加

対象: ses_work/gate_checker/agreement_checker.py
優先度: P1
根拠: 週末調査でledger import❌ can_spend❌ record❌ を確認済み。

## 背景
run_dual_review()がGPT-4o+Geminiを直叩き。common.ledgerを通さず台帳に記録されない。

## 修正1: import群末尾（from typing import Any の直後）に追加
```python
_SES_WORK = Path(__file__).resolve().parent.parent
import sys as _sys_cg
if str(_SES_WORK) not in _sys_cg.path:
    _sys_cg.path.insert(0, str(_SES_WORK))
try:
    from common.ledger import can_spend as _can_spend, record as _ledger_record
    _LEDGER_OK = True
except Exception:
    _LEDGER_OK = False
```

## 修正2: run_dual_review()内 ThreadPoolExecutorの直前に追加
```python
    if _LEDGER_OK:
        if not _can_spend(6000, 6000, "gpt-4o"):
            raise RuntimeError("[agreement_checker] CostGuard: 日次/月次上限超過")
```

## 修正3: call_gpt4o_simple()内 `judgment, verdict = parse_judgment(text)` の直前に追加
```python
            if _LEDGER_OK:
                try:
                    usage = data.get("usage", {})
                    _ledger_record(
                        usage.get("prompt_tokens", 3000),
                        usage.get("completion_tokens", 3000),
                        "gpt-4o", "agreement_checker_gpt"
                    )
                except Exception:
                    pass
```

## 修正4: call_gemini()内 `judgment, verdict = parse_judgment(text)` の直前に追加
```python
            if _LEDGER_OK:
                try:
                    _ledger_record(3000, 3000, "gemini-2.5-flash", "agreement_checker_gemini")
                except Exception:
                    pass
```

## 完了確認
```
cd /d "C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
python -c "import sys; sys.path.insert(0,'.'); from gate_checker.agreement_checker import run_dual_review, _LEDGER_OK; print(f'OK / ledger={_LEDGER_OK}')"
```
ledger=True が出ること。


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
