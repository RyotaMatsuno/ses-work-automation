# -*- coding: utf-8 -*-
"""Task AB: AA副作用修正の回帰テスト。"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from analyze_final import classify_by_rule

SKIP_CASES = [
    ("【7月/注力要員】Java3年/SpringBoot/55〜58万", "skip"),
    ("【PMO/7月稼働】システム更改に強み◆30歳（60万〜）", "skip"),
    ("【関西要員/7月】VB.net/SQL/50万/常駐可", "skip"),
]

PROJECT_RESCUE_CASES = [
    (
        "【元請け直】大学向けデジタル証明書SaaS開発支援/〜100万【Roots案件】",
        "project",
    ),
]

ENGINEER_RESCUE_CASES = [
    ("★新着★直個人【Goエンジニア 26歳/男性/6月~】", "engineer"),
    ("【VBA×Power BI｜業務改善・DX推進を一人称で担えるSE】", "engineer"),
]


@pytest.mark.parametrize("subj,expected", SKIP_CASES)
def test_skip_cases(subj, expected):
    assert classify_by_rule(subj, "") == expected


@pytest.mark.parametrize("subj,expected", PROJECT_RESCUE_CASES)
def test_project_rescue_cases(subj, expected):
    assert classify_by_rule(subj, "") == expected


@pytest.mark.parametrize("subj,expected", ENGINEER_RESCUE_CASES)
def test_engineer_rescue_cases(subj, expected):
    assert classify_by_rule(subj, "") == expected
