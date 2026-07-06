# -*- coding: utf-8 -*-
"""auto_classify_skills ルールベース分類のユニットテスト。"""

from __future__ import annotations

import sys
from pathlib import Path

MATCHING_V3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MATCHING_V3))

from auto_classify_skills import _classify_rule_based


def test_classify_garbage_symbol():
    cls, canonical = _classify_rule_based("】", {})
    assert cls == "garbage"
    assert canonical is None


def test_classify_canonical_via_alias():
    aliases = {"java": "Java"}
    cls, canonical = _classify_rule_based("Java", aliases)
    assert cls == "canonical"
    assert canonical == "Java"


def test_classify_suffix_cleaned():
    aliases = {"react": "React"}
    cls, canonical = _classify_rule_based("react案件", aliases)
    assert cls == "canonical_cleaned"
    assert canonical == "React"
