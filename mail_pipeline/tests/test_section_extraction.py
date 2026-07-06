"""Tests for Phase 3 section-aware skill extraction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline.skill_extractor import extract_skills, _section_aware_extract


def _has_skill(skills: list[str], name: str) -> bool:
    return any(name.lower() in s.lower() for s in skills)


def test_both_required_and_optional():
    body = """
■必須スキル
Java, Spring Boot, MySQL

■尚可スキル
Docker, Kubernetes
"""
    result = extract_skills("", body)
    assert _has_skill(result["required"], "java")
    assert _has_skill(result["required"], "spring")
    assert _has_skill(result["required"], "mysql")
    assert _has_skill(result["optional"], "docker")
    assert _has_skill(result["optional"], "kubernetes")


def test_required_only():
    body = """
【必須】
Python, Django, PostgreSQL
"""
    result = extract_skills("", body)
    assert _has_skill(result["required"], "python")
    assert _has_skill(result["required"], "django")
    assert len(result["optional"]) == 0


def test_no_section_header_fallback():
    """ヘッダーなしは従来通り全てrequiredに格納。"""
    body = "Java, Python, AWS を使ったシステム開発案件です。"
    result = extract_skills("", body)
    assert _has_skill(result["required"], "java")
    assert _has_skill(result["required"], "python")
    assert _has_skill(result["required"], "aws")
    assert len(result["optional"]) == 0


def test_required_header_variations():
    """複数の必須ヘッダーバリエーション"""
    for header in ["■必須", "必須スキル", "必須条件", "MUST", "必須要件"]:
        body = f"{header}\nJava, AWS\n\n備考\nその他情報"
        result = extract_skills("", body)
        assert _has_skill(result["required"], "java"), f"Header '{header}' should detect Java as required"


def test_optional_header_variations():
    """尚可が歓迎やWANTの場合"""
    for header in ["■歓迎", "歓迎スキル", "WANT", "あると尚可", "歓迎条件"]:
        body = f"■必須\nJava\n\n{header}\nDocker, Kubernetes"
        result = extract_skills("", body)
        assert _has_skill(result["optional"], "docker"), f"Header '{header}' should detect Docker as optional"
        assert _has_skill(result["required"], "java")


def test_section_break_stops_extraction():
    """セクション区切りでスキル抽出を停止する"""
    body = """
■必須
Java, Python

単価：60-80万円

Docker, Kubernetes
"""
    result = extract_skills("", body)
    assert _has_skill(result["required"], "java")
    assert _has_skill(result["required"], "python")
    assert not _has_skill(result["required"], "docker")
    assert not _has_skill(result["optional"], "docker")


def test_section_aware_extract_direct():
    """_section_aware_extract の直接テスト"""
    text = "【必須】\nJava\nPython\n\n【尚可】\nAWS\nDocker"
    result = _section_aware_extract(text)
    assert result["hit"] is True
    assert "java" in result["required"]
    assert "python" in result["required"]
    assert "aws" in result["optional"]
    assert "docker" in result["optional"]


def test_section_aware_no_header():
    """ヘッダーなしはhit=False"""
    text = "Java, Python, AWS の開発経験があること"
    result = _section_aware_extract(text)
    assert result["hit"] is False
