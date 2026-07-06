# -*- coding: utf-8 -*-
"""Task BG: 2層分類 classify_tier() テスト（代表30件）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analyze_final import classify_tier

# ── 代表テストケース（30件） ──────────────────────────────────────────────────

# strong_project ケース
def test_tier_strong_project_two_patterns():
    assert classify_tier("【案件】Java開発案件 案件概要あり 7月〜", "") == "strong_project"


def test_tier_strong_project_case_bracket():
    assert classify_tier("【案件情報】Python PMO 60万 8月開始", "") == "strong_project"


def test_tier_strong_project_keyword_count():
    assert classify_tier("案件No.001 基本設計〜運用 Java/Spring", "") == "strong_project"


def test_tier_strong_project_with_body():
    body = "案件概要\n勤務場所: 東京\n期間: 3ヶ月\n単価: 65万\n募集人数: 2名\n必須スキル: Java"
    # 「案件概要」「業務内容」の両パターンが件名・本文に揃えば strong_project
    assert classify_tier("案件概要 Java開発案件 業務内容 7月〜", "", body) == "strong_project"


def test_tier_strong_project_endrect():
    assert classify_tier("エンド直案件 AWS構築 65〜75万", "") == "strong_project"


def test_tier_strong_project_rush():
    assert classify_tier("急募案件 PMO 6月〜 60万", "") == "strong_project"


# strong_engineer ケース
def test_tier_strong_engineer_age_gender():
    assert classify_tier("【Java】35歳/男性 即日稼働可", "") == "strong_engineer"


def test_tier_strong_engineer_skillsheet():
    assert classify_tier("スキルシート送付 Javaエンジニア", "") == "strong_engineer"


def test_tier_strong_engineer_resume():
    assert classify_tier("経歴書添付 AWS/Python 3年", "") == "strong_engineer"


def test_tier_strong_engineer_recommend():
    assert classify_tier("おすすめ人材 PMO補佐", "") == "strong_engineer"


def test_tier_strong_engineer_focus():
    assert classify_tier("注力要員 Java/Spring 5年", "") == "strong_engineer"


def test_tier_strong_engineer_direct():
    assert classify_tier("直個人 TypeScript 3年 40万", "") == "strong_engineer"


def test_tier_strong_engineer_direct_freelance():
    assert classify_tier("直フリーランス Go/AWS 40歳 男性", "") == "strong_engineer"


def test_tier_strong_engineer_mass_dist():
    assert classify_tier("人材配信 弊社プロパー多数", "") == "strong_engineer"


def test_tier_strong_engineer_young():
    assert classify_tier("若手人材 Java 2年 稼働可", "") == "strong_engineer"


def test_tier_strong_engineer_veteran():
    assert classify_tier("ベテランエンジニア AWS/Python 10年", "") == "strong_engineer"


def test_tier_strong_engineer_referral():
    assert classify_tier("人材ご紹介 弊社プロパー AWS/Python", "") == "strong_engineer"


def test_tier_strong_engineer_distribution():
    assert classify_tier("要員配信 5名 7月稼働可", "") == "strong_engineer"


def test_tier_strong_engineer_company_intro():
    assert classify_tier("弊社プロパーご紹介 Java 5年", "") == "strong_engineer"


def test_tier_strong_engineer_body_skillsheet():
    body = "スキルシート添付しております。ご確認ください。"
    assert classify_tier("エンジニアご紹介", "", body) == "strong_engineer"


# ambiguous ケース
def test_tier_ambiguous_greeting():
    assert classify_tier("お世話になっております", "") == "ambiguous"


def test_tier_ambiguous_seminar():
    assert classify_tier("AIセミナーのご案内", "") == "ambiguous"


def test_tier_ambiguous_single_project_kw():
    assert classify_tier("案件について", "") == "ambiguous"


def test_tier_ambiguous_generic_ses():
    assert classify_tier("SES案件のご相談", "") == "ambiguous"


def test_tier_ambiguous_newsletter():
    assert classify_tier("メルマガ配信停止のご案内", "") == "ambiguous"


def test_tier_ambiguous_no_content():
    assert classify_tier("", "") == "ambiguous"


def test_tier_ambiguous_inquiry():
    assert classify_tier("ご確認のお願い", "") == "ambiguous"


# edge cases
def test_tier_suppress_strong_project_when_human_marker():
    # 人材マーカーがある場合は strong_project にしない
    result = classify_tier("35歳/男性 Java案件 元請直 エンド直", "")
    # strong_engineer になるべき
    assert result == "strong_engineer"


def test_tier_returns_one_of_three_values():
    for subj in ["test", "案件", "要員配信", "Java開発 案件概要 必須スキル: Java 期間: 3ヶ月"]:
        result = classify_tier(subj, "")
        assert result in ("strong_project", "strong_engineer", "ambiguous"), f"Unexpected: {result!r} for {subj!r}"
