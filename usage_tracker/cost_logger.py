"""
cost_logger.py - 各スクリプトからAPIコスト1行をJSONLに追記する
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from usage_tracker.cost_calculator import calc_cost_usd

LOG_PATH = Path(__file__).resolve().parent / "cost_log.jsonl"


def log_cost(
    script_name: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> None:
    try:
        cost_usd = calc_cost_usd(model, input_tokens, output_tokens, cached_tokens)
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "script": script_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": round(cost_usd, 8),
        }
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[cost_logger] ERROR: {e}", flush=True)
