"""Tests for Phase 3: price_extractor validate_price()."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from mail_pipeline.price_extractor import validate_price

@pytest.mark.parametrize("value,raw_text,expected_val,expected_reason", [
    (65, "単価65万円", 65.0, None),
    (75, "", 75.0, None),
    (600, "想定年収600万", 50.0, "annual_converted"),
    (430000, "単価情報", None, "anomaly_nulled"),
    (3.5, "日額3.5万", 70.0, "daily_converted"),
    (1.5, "単価1.5万円", None, "anomaly_nulled"),
    (None, "", None, None),
    (200, "MAX200万", 200.0, None),
    (20, "月額20万", 20.0, None),
    (250, "年収250万", 20.8, "annual_converted"),
    (250, "年俸250万", 20.8, "annual_converted"),
    (300, "賞与込300万", 25.0, "annual_converted"),
    (5, "日給5万", 100.0, "daily_converted"),
])
def test_validate_price(value, raw_text, expected_val, expected_reason):
    result_val, reason = validate_price(value, raw_text)
    assert result_val == expected_val, f"value={value} raw={raw_text!r}: expected {expected_val}, got {result_val}"
    assert reason == expected_reason, f"value={value} raw={raw_text!r}: expected reason={expected_reason!r}, got {reason!r}"
