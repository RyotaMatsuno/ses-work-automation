from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

from notion_client import realtime_match_window_hours

WORKER_PATH = Path(__file__).resolve().parent.parent / "worker" / "realtime_match_worker.py"
SPEC = importlib.util.spec_from_file_location("realtime_match_worker", WORKER_PATH)
worker = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(worker)


def test_realtime_match_window_hours():
    assert realtime_match_window_hours({"案件種別": "急募"}) == 2.0
    assert realtime_match_window_hours({"案件名": "中長期Java案件"}) == 6.0
    assert realtime_match_window_hours({}) == 3.0


def test_idempotency_key_is_per_day():
    key = worker._today_key("abc-123")
    assert key.startswith("abc-123:")


def test_case_within_window_respects_timer():
    now = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)
    recent = {
        "created_time": "2026-06-23T11:30:00+00:00",
        "案件種別": "急募",
    }
    old = {
        "created_time": "2026-06-23T08:00:00+00:00",
        "案件種別": "急募",
    }
    assert worker._case_within_window(recent, now.astimezone(worker.JST)) is True
    assert worker._case_within_window(old, now.astimezone(worker.JST)) is False
