# -*- coding: utf-8 -*-
"""Task AC: pre-skip 人材専用シグナル回帰テスト。"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from analyze_final import classify_by_rule

SKIP_CASES = [
    (
        "弊社正社員のご紹介 JP1/AWS/運用保守【株式会社エムティークラウド】",
        "skip",
    ),
    (
        "弊社正社員のご紹介 Java/TypeScript/Swift【株式会社エムティークラウド】",
        "skip",
    ),
]

PROJECT_CASES = [
    ("[WT案件]Linux・C言語/55万/15名枠/品川シーサイド", "project"),
    ("【BTM案件】NW/78万/3名募集/品川シーサイド", "project"),
]


@pytest.mark.parametrize("subj,expected", SKIP_CASES)
def test_skip_human_only_cases(subj, expected):
    assert classify_by_rule(subj, "") == expected


@pytest.mark.parametrize("subj,expected", PROJECT_CASES)
def test_project_case_rescue(subj, expected):
    assert classify_by_rule(subj, "") == expected
