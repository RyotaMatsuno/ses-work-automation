from __future__ import annotations

import json
import os
import os as _os
import sys as _sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), ".."))
try:
    from common.ledger import can_spend as _global_can_spend
except ImportError:
    _global_can_spend = None

BASE_DIR = Path(__file__).resolve().parent


class CostGuard:
    DAILY_CALL_LIMIT = 1500
    DAILY_COST_LIMIT_USD = 1.00
    MONTHLY_DEGRADE_USD = 5.00
    MONTHLY_STOP_USD = 6.00
    COST_LOG_PATH = BASE_DIR.parent / "usage_tracker" / "cost_log.jsonl"
    # gpt-4.1-nano: input $0.10/1M, output $0.40/1M (2026-06時点)
    LLM_INPUT_RATE_USD = 0.10 / 1_000_000
    LLM_OUTPUT_RATE_USD = 0.40 / 1_000_000

    def __init__(self, cost_log_path: str | Path = COST_LOG_PATH) -> None:
        self.cost_log_path = Path(cost_log_path)

    def can_call(self, est_input_tokens: int, est_output_tokens: int) -> bool:
        if _global_can_spend is not None:
            from config import DEFAULT_STRUCTURER_MODEL

            if not _global_can_spend(est_input_tokens, est_output_tokens, DEFAULT_STRUCTURER_MODEL):
                return False
        daily = self._get_daily_stats()
        if int(daily["api_calls"]) >= self.DAILY_CALL_LIMIT:
            return False
        est_cost = self._estimate_cost(est_input_tokens, est_output_tokens)
        if float(daily["total_cost_usd"]) + est_cost > self.DAILY_COST_LIMIT_USD:
            return False
        if self._get_monthly_cost() >= self.MONTHLY_STOP_USD:
            return False
        return True

    def record_cost(self, input_tokens: int, output_tokens: int, model: str) -> None:
        cost = self._estimate_cost(input_tokens, output_tokens)
        self.cost_log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "script": "matching_v3",
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost,
        }
        with self.cost_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_model(self) -> str:
        from config import DEFAULT_STRUCTURER_MODEL

        if self._get_monthly_cost() >= self.MONTHLY_DEGRADE_USD:
            return os.environ.get("FALLBACK_MODEL", "gemini-2.0-flash")
        return os.environ.get("STRUCTURER_MODEL", DEFAULT_STRUCTURER_MODEL)

    def _get_monthly_cost(self) -> float:
        now = datetime.now(timezone.utc)
        return self._sum_cost(lambda dt: dt.year == now.year and dt.month == now.month)

    def _get_daily_stats(self) -> dict[str, float | int]:
        today = datetime.now(timezone.utc).date()
        calls = 0
        total = 0.0
        for entry in self._iter_entries():
            if entry.get("script") != "matching_v3":
                continue
            dt = self._parse_ts(entry.get("ts"))
            if dt and dt.date() == today:
                calls += 1
                total += float(entry.get("cost_usd") or 0.0)
        return {"api_calls": calls, "total_cost_usd": total}

    def _sum_cost(self, predicate) -> float:
        total = 0.0
        for entry in self._iter_entries():
            if entry.get("script") != "matching_v3":
                continue
            dt = self._parse_ts(entry.get("ts"))
            if dt and predicate(dt):
                total += float(entry.get("cost_usd") or 0.0)
        return total

    def _iter_entries(self) -> list[dict[str, Any]]:
        if not self.cost_log_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.cost_log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries

    @classmethod
    def _estimate_cost(cls, input_tokens: int, output_tokens: int) -> float:
        return input_tokens * cls.LLM_INPUT_RATE_USD + output_tokens * cls.LLM_OUTPUT_RATE_USD

    @staticmethod
    def _parse_ts(value: Any) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
