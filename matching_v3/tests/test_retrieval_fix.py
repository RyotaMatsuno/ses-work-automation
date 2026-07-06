from __future__ import annotations

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from matcher import (
    SkillNormalizer,
    build_skill_index,
    filter_engineers_by_required_skills,
)

ALIASES_PATH = "skill_aliases.json"


def _normalizer() -> SkillNormalizer:
    return SkillNormalizer(ALIASES_PATH)


def _make_engineer(eid: str, skills: list[str]) -> dict:
    return {"id": eid, "スキル": skills}


def test_partial_match_passes():
    """5スキル中3マッチ → 候補に含まれる (min_match = ceil(0.5*5) = 3)"""
    normalizer = _normalizer()
    required = ["Java", "Python", "AWS", "Docker", "Kubernetes"]
    eng = _make_engineer("eng1", ["Java", "Python", "AWS"])
    index = build_skill_index([eng], normalizer)
    result = filter_engineers_by_required_skills([eng], normalizer, index, required)
    assert any(e["id"] == "eng1" for e in result)


def test_below_threshold_excluded():
    """5スキル中1マッチ → 除外 (min_match=3 > 1)"""
    normalizer = _normalizer()
    required = ["Java", "Python", "AWS", "Docker", "Kubernetes"]
    eng = _make_engineer("eng1", ["Java"])
    index = build_skill_index([eng], normalizer)
    result = filter_engineers_by_required_skills([eng], normalizer, index, required)
    assert not any(e["id"] == "eng1" for e in result)


def test_min_one_match():
    """2スキル中1マッチ → 含まれる (min_match = max(1, ceil(0.5*2)) = 1)"""
    normalizer = _normalizer()
    required = ["Java", "Python"]
    eng = _make_engineer("eng1", ["Java"])
    index = build_skill_index([eng], normalizer)
    result = filter_engineers_by_required_skills([eng], normalizer, index, required)
    assert any(e["id"] == "eng1" for e in result)


def test_no_resolved_skills_returns_empty():
    """辞書に存在しない無効スキルのみ → 空リスト"""
    normalizer = _normalizer()
    required = ["存在しないスキルXYZ_999_テスト"]
    eng = _make_engineer("eng1", ["Java"])
    index = build_skill_index([eng], normalizer)
    result = filter_engineers_by_required_skills([eng], normalizer, index, required)
    assert result == []


def test_candidate_cap_at_100():
    """150名全員がJavaを持つ → 結果は100名にキャップ"""
    normalizer = _normalizer()
    required = ["Java"]
    engineers = [_make_engineer(f"eng{i}", ["Java"]) for i in range(150)]
    index = build_skill_index(engineers, normalizer)
    result = filter_engineers_by_required_skills(engineers, normalizer, index, required)
    assert len(result) == 100


def test_empty_engineers_returns_empty():
    """エンジニアリスト空 → 空リスト"""
    normalizer = _normalizer()
    required = ["Java"]
    index = build_skill_index([], normalizer)
    result = filter_engineers_by_required_skills([], normalizer, index, required)
    assert result == []


def test_backward_compat_full_match():
    """全スキル一致 → 当然含まれる"""
    normalizer = _normalizer()
    required = ["Java", "Python", "AWS"]
    eng = _make_engineer("eng1", ["Java", "Python", "AWS"])
    index = build_skill_index([eng], normalizer)
    result = filter_engineers_by_required_skills([eng], normalizer, index, required)
    assert any(e["id"] == "eng1" for e in result)
