"""Tests for skill validation in skill_extractor.py (Task AA / Phase 1 / Precision R3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline.skill_extractor import (
    filter_skills,
    normalize_extracted_skill,
    strip_business_suffix,
    validate_skill,
)

VALID_SKILLS = [
    "Java",
    "AWS",
    "Spring Boot",
    "C#",
    "Python",
    "Docker",
    "React",
    "インフラ",
    "ネットワーク",
    "要件定義",
    "基本設計",
    # 1D: 短いASCII（KNOWN_SKILLSに存在）
    "SE",
    "PM",
    "PL",
    "PMO",
    "QA",
    "iOS",
    "AI",
    "ML",
]

INVALID_SKILLS = [
    "65~75万円",
    "110~150万円",
    "*弊社増員枠",
    "8月相談可能☆常駐cobol案件☆55歳まで",
    "50万円",
    "7月〜",
    "即日",
    "2名",
    "",
    "a",
    # 1B: 新規追加ゴミパターン
    "】",
    "△",
    ">",
    "6月",
    "7月",
    "フルリモート",
    "リモート",
    "スキル",
    "スキル:",
    "ではありますが少し不足の場合はコメントと共にご提案ください",
    "条件の各項目について",
]

SAMPLE_ALIASES = {
    "c言語": "C言語",
    "c": "C言語",
    "windows": "Windows",
    "ut": "単体テスト",
    "unit test": "単体テスト",
    "firewall": "Firewall",
    "fw": "Firewall",
    "vba": "VBA",
    "excel vba": "VBA",
    "access": "Access",
    "pl/sql": "PL/SQL",
    "plsql": "PL/SQL",
    "llm": "LLM",
}


def test_valid_skills_accepted():
    for s in VALID_SKILLS:
        is_valid, _ = validate_skill(s)
        assert is_valid, f"Should accept: {s!r}"


def test_invalid_skills_rejected():
    for s in INVALID_SKILLS:
        is_valid, _ = validate_skill(s)
        assert not is_valid, f"Should reject: {s!r}"


def test_allowlist_overrides_blacklist():
    """辞書allowlistにあれば即accept (C言語, Windows OS知識 etc.)"""
    is_valid, canonical = validate_skill("C言語", SAMPLE_ALIASES)
    assert is_valid, "C言語 should be accepted via allowlist"
    assert canonical == "C言語"

    is_valid2, canonical2 = validate_skill("UT", SAMPLE_ALIASES)
    assert is_valid2, "UT should be accepted via allowlist"
    assert canonical2 == "単体テスト"


def test_allowlist_normalize_suffix():
    """suffix除去後に辞書ヒット: 'firewallの構築経験' -> 'Firewall'"""
    is_valid, canonical = validate_skill("firewallの構築経験", SAMPLE_ALIASES)
    assert is_valid, "firewallの構築経験 should be accepted after suffix strip"
    assert canonical == "Firewall", f"Expected 'Firewall', got {canonical!r}"

    is_valid2, canonical2 = validate_skill("Javaでの開発経験", {"java": "Java"})
    assert is_valid2
    assert canonical2 == "Java"


def test_normalize_extracted_skill():
    """normalize_extracted_skill()のsuffix除去テスト。"""
    assert normalize_extracted_skill("firewallの構築経験") == "firewall"
    assert normalize_extracted_skill("Javaでの開発経験") == "Java"
    assert normalize_extracted_skill("Python開発経験") == "Python"
    assert normalize_extracted_skill("経験") == ""
    assert normalize_extracted_skill("管理") == ""


def test_filter_skills_basic():
    """filter_skills returns valid skills as list."""
    valid, rejected, cleaned = filter_skills(["Java", "Python", "スキル", "7月〜"])
    assert "Java" in valid
    assert "Python" in valid
    assert "スキル" not in valid
    assert "7月〜" not in valid
    assert "スキル" in rejected


def test_filter_skills_with_aliases():
    """filter_skills with aliases returns canonical forms."""
    valid, rejected, cleaned = filter_skills(["C言語", "VBA", "スキル"], SAMPLE_ALIASES)
    assert "C言語" in valid
    assert "VBA" in valid
    assert "スキル" not in valid


def test_filter_skills_dedup():
    """filter_skills deduplicates results."""
    valid, rejected, cleaned = filter_skills(["Java", "java", "JAVA"])
    assert len(valid) == len(set(valid))


def test_filter_skills_empty_input():
    valid, rejected, cleaned = filter_skills([])
    assert valid == []


def test_suffix_clean_react():
    valid, rejected, cleaned = filter_skills(["react案件"])
    assert any("react" in r.lower() for r in valid)


def test_suffix_clean_java():
    valid, rejected, cleaned = filter_skills(["java要員"])
    assert any("java" in r.lower() for r in valid)


def test_strip_business_suffix():
    assert strip_business_suffix("react案件") == "react"
    assert strip_business_suffix("java要員") == "java"
    assert strip_business_suffix("Python") == "Python"
    assert strip_business_suffix("人材募集") == "人材"
