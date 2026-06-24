# -*- coding: utf-8 -*-
"""analyze_final rule classification tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from analyze_final import classify_by_rule


def test_helpdesk_is_project_not_skip():
    assert classify_by_rule("【案件】ヘルプデスク 品川 7月〜 35万", "sales@example.com") == "project"


def test_engineer_intro_is_engineer():
    assert classify_by_rule("【要員】Java 3年 30万 男性", "sales@example.com") == "engineer"


def test_seminar_is_skip():
    assert classify_by_rule("AI活用セミナーのご案内", "sales@example.com") == "skip"


def test_ambiguous_goes_unknown():
    assert classify_by_rule("お世話になっております", "sales@example.com") == "unknown"


def test_btm_case_is_project():
    assert classify_by_rule("【BTM案件】Java開発", "sales@example.com") == "project"


def test_nbw_case_is_project():
    assert classify_by_rule("【NBW案件】PMO", "sales@example.com") == "project"


def test_btm_engineer_stays_engineer():
    assert classify_by_rule("【BTM要員】Java/5年/男性", "sales@example.com") == "engineer"


def test_btm_case_with_yoin_priority():
    assert classify_by_rule("【BTM案件】要員ご紹介", "sales@example.com") == "project"
