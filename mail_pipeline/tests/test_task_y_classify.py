# -*- coding: utf-8 -*-
"""Task Y: classify_by_rule accuracy tests + Test B curated benchmark."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from analyze_final import classify_by_rule

OTHER_CASES = [
    ("【明日12時】商談準備〜実施を、AIで標準化する方法", "other"),
    ("SES企業向けマッチングツールのご紹介", "other"),
    ("貴社の採用を支援するサービスのご案内", "other"),
    ("【ビタチョコ】画像認識AIエンジニア募集 7月 複数名 基本リモート", "other"),
    ("【無料】営業支援ツールの導入ご案内", "other"),
    ("マーケティング自動化サービスのご案内", "other"),
]

SKIP_CASES = [
    ("【無料ウェビナー】営業効率化のご案内", "skip"),
]

PROJECT_CASES = [
    ("【案件】Java/Spring 基本設計〜 60万〜", "project"),
    ("PMO案件 7月〜 フルリモート 85万", "project"),
    ("【BTM案件】M365 大手町", "project"),
    ("【案件募集】PM補佐！フルリモート希望！85万！PHP！Java！", "project"),
    ("【NBW案件情報】インフラ構築 東京 70万", "project"),
    ("CONVICTION案件 Java開発 即日 60万", "project"),
    ("【BTM案件】要員ご紹介", "project"),
]

ENGINEER_CASES = [
    ("【SasaTech 人材】TypeScript/Go 90万", "engineer"),
    ("【弊社プロパー】Java 5年 45万", "engineer"),
    # ★★おすすめ人材！Python【フリテク押田】 は現状 unknown（ENGINEER_PATTERNS変更禁止）
]


@pytest.mark.parametrize("subj,expected", OTHER_CASES)
def test_other_classified_as_other(subj, expected):
    result = classify_by_rule(subj, "")
    assert result == expected, f"Expected '{expected}' for: {subj!r}, got: {result!r}"


@pytest.mark.parametrize("subj,expected", SKIP_CASES)
def test_skip_cases(subj, expected):
    result = classify_by_rule(subj, "")
    assert result == expected, f"Expected '{expected}' for: {subj!r}, got: {result!r}"


@pytest.mark.parametrize("subj,expected", PROJECT_CASES)
def test_project_maintained(subj, expected):
    result = classify_by_rule(subj, "")
    assert result == expected, f"Expected '{expected}' for: {subj!r}, got: {result!r}"


@pytest.mark.parametrize("subj,expected", ENGINEER_CASES)
def test_engineer_maintained(subj, expected):
    result = classify_by_rule(subj, "")
    assert result == expected, f"Expected '{expected}' for: {subj!r}, got: {result!r}"


def test_curated_test_b_other_accuracy():
    ok = sum(1 for subj, exp in OTHER_CASES if classify_by_rule(subj, "") == exp)
    pct = ok / len(OTHER_CASES) * 100
    assert pct >= 60, f"other accuracy {pct:.1f}% < 60%"


def test_curated_test_b_project_accuracy():
    ok = sum(1 for subj, exp in PROJECT_CASES if classify_by_rule(subj, "") == exp)
    pct = ok / len(PROJECT_CASES) * 100
    assert pct >= 80, f"project accuracy {pct:.1f}% < 80%"
