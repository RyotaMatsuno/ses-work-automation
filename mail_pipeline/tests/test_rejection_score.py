# -*- coding: utf-8 -*-
"""Phase 1: _rejection_score スコアベース拒否テスト。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline.skill_extractor import _rejection_score, validate_skill

# score >= 3 で拒否されるべきケース
REJECT = [
    "テストメンバーのタスク管理",
    "運用保守まで一貫した業務経験",
    "および品質向上観点での提案経験",
    "調整・推進力",
    "基幹システム開発における上流工程の経験",
]

# score < 3 で通すべきケース（辞書にある場合はStep1-2で通過）
ACCEPT = [
    "要件定義",
    "基本設計",
    "Oracle",
    "AWS構築",
    "ネットワーク設計",
    "プロジェクトマネジメント",
]


def test_reject_cases_score_ge_3():
    for v in REJECT:
        s = _rejection_score(v)
        assert s >= 3, f"Expected score>=3 for {v!r}, got {s}"


def test_accept_cases_score_lt_3():
    for v in ACCEPT:
        s = _rejection_score(v)
        assert s < 3, f"Expected score<3 for {v!r}, got {s}"


def test_reject_cases_validate_skill():
    """REJECT ケースは validate_skill でも False になる（辞書にないため）。"""
    for v in REJECT:
        ok, _ = validate_skill(v, {})
        assert not ok, f"validate_skill should reject: {v!r}"
