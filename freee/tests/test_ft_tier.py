# -*- coding: utf-8 -*-
"""FT tiered gross profit rate tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sheets_reader import _ft_entry, ft_tier_rate


def test_ft_tier_rate_9_cases():
    assert ft_tier_rate(9) == 0.68


def test_ft_tier_rate_11_cases():
    assert ft_tier_rate(11) == 0.75


def test_ft_tier_rate_14_cases():
    assert ft_tier_rate(14) == 0.80


def test_ft_entry_uses_tier_rate_for_normal():
    entry, reason = _ft_entry(
        row=[],
        cfg={},
        site_days=45,
        profit=100_000,
        tantou="通常",
        name="テスト太郎",
        ft_rate=0.75,
    )
    assert reason is None
    assert entry is not None
    assert entry["seikyu"] == 75_000
    assert "75%" in entry["rule"]


def test_ft_entry_kosaka_stays_48_percent():
    entry, reason = _ft_entry(
        row=[],
        cfg={},
        site_days=45,
        profit=100_000,
        tantou="小坂折半",
        name="テスト次郎",
        ft_rate=0.80,
    )
    assert reason is None
    assert entry is not None
    assert entry["seikyu"] == 48_000
    assert "48%" in entry["rule"]
