# Phase2 SPEC: common/ledger.py

## 概要
全LLMコンポーネントが必ず通る単一の共有コストゲートモジュール。
13MBファイルの全読みをなくし、incremental state fileで高速化する。

## ファイル構成
```
ses_work/common/__init__.py   # 空
ses_work/common/ledger.py     # 本体
ses_work/common/cost_state.json  # 実行時に自動生成（コミット不要）
```

## ledger.py の全実装

```python
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # ses_work/
STATE_FILE = Path(__file__).resolve().parent / "cost_state.json"
COST_LOG = BASE_DIR / "usage_tracker" / "cost_log.jsonl"

# グローバル上限
DAILY_SOFT_USD  = 6.0
DAILY_HARD_USD  = 8.0
MONTHLY_USD     = 140.0

# モデル別単価（per 1M tokens: input, output）
RATES: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001":   (1.0,  5.0),
    "claude-haiku-4-5":            (1.0,  5.0),
    "claude-sonnet-4-6":           (3.0, 15.0),
    "claude-sonnet-4-5":           (3.0, 15.0),
    "claude-sonnet-4-20250514":    (3.0, 15.0),
    "claude-sonnet-4-6-20250514":  (3.0, 15.0),
}
_DEFAULT_RATE = (1.0, 5.0)


def _estimate(in_tokens: int, out_tokens: int, model: str) -> float:
    r = RATES.get(model, _DEFAULT_RATE)
    return in_tokens * r[0] / 1_000_000 + out_tokens * r[1] / 1_000_000


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_state() -> dict:
    today = _now_date()
    month = _now_month()
    s: dict = {}
    if STATE_FILE.exists():
        try:
            s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            s = {}
    # 月またぎリセット
    if s.get("month") != month:
        s = {"date": today, "month": month, "daily_usd": 0.0, "monthly_usd": 0.0, "daily_calls": 0}
    # 日またぎリセット
    elif s.get("date") != today:
        s = {"date": today, "month": month, "daily_usd": 0.0, "monthly_usd": s.get("monthly_usd", 0.0), "daily_calls": 0}
    return s


def _save_state(s: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _append_log(entry: dict) -> None:
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def can_spend(est_in: int = 200, est_out: int = 300,
              model: str = "claude-haiku-4-5-20251001") -> bool:
    """API呼び出し前に確認。Falseならスキップすること。"""
    s = _load_state()
    est = _estimate(est_in, est_out, model)
    if s["daily_usd"] + est > DAILY_HARD_USD:
        return False
    if s["monthly_usd"] + est > MONTHLY_USD:
        return False
    return True


def record(in_tokens: int, out_tokens: int, model: str, script: str) -> None:
    """API呼び出し成功後に必ず呼ぶ。コストを記録する。"""
    cost = _estimate(in_tokens, out_tokens, model)
    s = _load_state()
    s["daily_usd"] = round(s["daily_usd"] + cost, 8)
    s["monthly_usd"] = round(s["monthly_usd"] + cost, 8)
    s["daily_calls"] = s.get("daily_calls", 0) + 1
    _save_state(s)
    _append_log({
        "ts":            datetime.now(timezone.utc).isoformat(),
        "script":        script,
        "model":         model,
        "input_tokens":  in_tokens,
        "output_tokens": out_tokens,
        "cost_usd":      cost,
    })


def daily_total() -> float:
    return _load_state()["daily_usd"]


def monthly_total() -> float:
    return _load_state()["monthly_usd"]
```
