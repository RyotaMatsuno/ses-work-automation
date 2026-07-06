# -*- coding: utf-8 -*-
"""Tests for merge_policy."""

from __future__ import annotations

import sys
from pathlib import Path

SES_WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SES_WORK))

from scripts.merge_policy import should_update


def test_fill_if_empty():
    ok, reason = should_update("rate_type", None, "fixed_range", 0.8)
    assert ok and reason == "fill_if_empty"


def test_never_overwrite_skills():
    ok, reason = should_update("必要スキル", ["Java"], ["Python"], 0.9)
    assert not ok and reason == "never_overwrite"


def test_replace_zero_rate():
    ok, reason = should_update("単価（万円）", 0, 65, 0.8)
    assert ok and reason == "replace_zero_with_extracted"


def test_keep_existing_location():
    ok, reason = should_update("勤務地", "東京", "大阪", 0.9)
    assert not ok
