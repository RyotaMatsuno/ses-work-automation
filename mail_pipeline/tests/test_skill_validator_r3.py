# -*- coding: utf-8 -*-
"""Round 3 validate_skill allowlist-first テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline.skill_extractor import (
    filter_skills,
    load_skill_aliases,
    normalize_extracted_skill,
    validate_skill,
)


def test_c_language_accepted():
    aliases = load_skill_aliases()
    aliases = {**aliases, "c言語": "C"}
    ok, canon = validate_skill("C言語", aliases)
    assert ok
    assert canon == "C"


def test_windows_os_knowledge_accepted():
    aliases = load_skill_aliases()
    aliases = {**aliases, "windows os知識": "Windows"}
    ok, canon = validate_skill("Windows OS知識", aliases)
    assert ok
    assert canon == "Windows"


def test_firewall_experience_normalized():
    aliases = load_skill_aliases()
    aliases = {**aliases, "firewall": "Firewall"}
    ok, canon = validate_skill("firewallの構築経験", aliases)
    assert ok
    assert canon == "Firewall"


def test_generic_only_rejected():
    ok, _ = validate_skill("制限の管理の経験", {})
    assert not ok


def test_ut_maps_to_unit_test():
    aliases = load_skill_aliases()
    aliases = {**aliases, "ut": "単体テスト"}
    ok, canon = validate_skill("UT", aliases)
    assert ok
    assert canon == "単体テスト"
