# -*- coding: utf-8 -*-
"""Phase 2: extract_price ルールベース単価抽出テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from recover_prices import extract_price


def test_standard_price():
    assert extract_price("単価: 65万") == 65


def test_range_lower():
    assert extract_price("55~65万") == 55


def test_yen_conversion():
    assert extract_price("650,000円/月") == 65


def test_reject_annual():
    assert extract_price("年収600万") is None


def test_reject_out_of_range_low():
    assert extract_price("単価: 5万") is None


def test_reject_out_of_range_high():
    assert extract_price("単価: 300万") is None


def test_monthly_label():
    assert extract_price("月額60〜70万") == 60


def test_budget_label():
    assert extract_price("予算：70万") == 70


def test_empty():
    assert extract_price("") is None


def test_no_price():
    assert extract_price("Javaの案件です。経験3年以上。") is None
