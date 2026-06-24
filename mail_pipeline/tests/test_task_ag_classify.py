# -*- coding: utf-8 -*-
"""Task AG: 未分類メール分類ルール拡張テスト。"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from analyze_final import classify_by_rule

TASK_AG_CASES = [
    ("【関西要員/7月】TypeScriptエンジニア 60万", "skip"),
    ("【案件】8月案件/SAP PMO 70万", "project"),
    ("★C++ エンジニア/要件定義～/常駐可/7月～★", "engineer"),
    ("【7月案件/〜70万】★急募/面談調整中★フルリモ", "project"),
    ("人材【金額調整しました！PHP, Node.js,TypeScript/45歳/男性/即日〜】874", "engineer"),
    ("TypeScriptエンジニア/詳細設計～/リモート併用/8月～★", "engineer"),
    ("【弊社正社員】　7月～/若手のJavaエンジニア", "engineer"),
    ("【常駐可能！】長期案件対応可能なサポートエンジニア！", "engineer"),
]


@pytest.mark.parametrize("subj,expected", TASK_AG_CASES)
def test_task_ag_unclassified_examples(subj, expected):
    assert classify_by_rule(subj, "") == expected


def test_unknown_fallback_never_returns_unknown_for_mass_talent():
    samples = [
        "★PHPエンジニア /要件定義〜/フルリモート(週1出社相談可)/7月～★",
        "人材｜Python、Java、C#、TypeScript、Ruby、VB.NET、VB｜顧客折衝",
    ]
    for subj in samples:
        assert classify_by_rule(subj, "") != "unknown"
