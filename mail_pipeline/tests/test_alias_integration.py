# -*- coding: utf-8 -*-
"""Phase 2 v2: skill_aliases.json 統合テスト。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline.skill_extractor import (
    _get_known_skills,
    _load_skill_aliases,
    _section_aware_extract,
    extract_skills,
    validate_skill,
)


def test_load_skill_aliases_returns_dict():
    aliases = _load_skill_aliases()
    assert isinstance(aliases, dict)
    assert len(aliases) > 300


def test_c_language_resolved():
    aliases = _load_skill_aliases()
    assert aliases.get("c言語") == "C"


def test_vba_resolved():
    aliases = _load_skill_aliases()
    assert aliases.get("vba") == "VBA"


def test_extract_skills_uses_aliases():
    result = extract_skills("【Java/C言語案件】", "必須スキル: Java, C言語, VBA")
    joined = " ".join(result["required"]).lower()
    assert "java" in joined or "c" in joined


def test_known_skills_from_json():
    ks = _get_known_skills()
    assert "java" in ks
    assert "c言語" in ks
    assert "vba" in ks


def test_blacklist_still_works():
    is_valid, _ = validate_skill("65~75万円")
    assert not is_valid


def test_section_aware_still_works():
    text = "■必須\nJava\nSpring\n■尚可\nAWS"
    result = _section_aware_extract(text)
    assert result["hit"]
    assert "java" in result["required"]
    assert "aws" in result["optional"]
