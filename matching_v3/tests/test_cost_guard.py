from __future__ import annotations

import json
from datetime import datetime, timezone

from cost_guard import CostGuard


def _write_cost(path, cost: float) -> None:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "script": "matching_v3",
        "model": "claude-haiku-4-5-20251001",
        "input_tokens": 1,
        "output_tokens": 1,
        "cost_usd": cost,
    }
    path.write_text(json.dumps(entry, ensure_ascii=False) + "\n", encoding="utf-8")


def test_can_call_false_when_daily_cost_exceeds_limit(tmp_path):
    path = tmp_path / "cost_log.jsonl"
    _write_cost(path, 1.0)
    guard = CostGuard(path)

    assert guard.can_call(1, 1) is False


def test_can_call_false_when_monthly_stop_exceeds_limit(tmp_path):
    path = tmp_path / "cost_log.jsonl"
    _write_cost(path, 6.0)
    guard = CostGuard(path)

    assert guard.can_call(1, 1) is False


def test_get_model_returns_fallback_when_monthly_degrade_exceeds_limit(tmp_path, monkeypatch):
    path = tmp_path / "cost_log.jsonl"
    _write_cost(path, 5.0)
    monkeypatch.setenv("FALLBACK_MODEL", "gemini-test")
    guard = CostGuard(path)

    assert guard.get_model() == "gemini-test"
