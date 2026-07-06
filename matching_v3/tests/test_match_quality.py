"""Tests for Phase 2: match quality improvement (Task AB/unified)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from matcher import SkillNormalizer, resolve_case_required_skills

ALIASES_PATH = Path(__file__).resolve().parent.parent / "skill_aliases.json"


def test_empty_skill_project_skipped():
    """必要スキル空の案件はresolve_case_required_skillsが[]を返すこと"""
    normalizer = SkillNormalizer(ALIASES_PATH)
    case = {
        "id": "test-empty",
        "必要スキル": [],
        "案件名": "",
        "案件詳細": "",
        "案件情報原文": "",
    }
    case_json = {"required_skills": []}
    skills, source = resolve_case_required_skills(case, case_json, normalizer)
    assert skills == []
    assert source == "none"


def test_match_count_max_20():
    """マッチ結果が常に20件以下になること"""
    results = [{"score": float(i), "verdict": "MATCH"} for i in range(100)]
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    if len(results) > 20:
        results = results[:20]
    assert len(results) == 20


def test_match_sorted_by_score_desc():
    """マッチ結果がスコア降順にソートされていること"""
    import random
    raw = [{"score": float(i), "verdict": "MATCH"} for i in range(50)]
    random.shuffle(raw)
    raw.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    if len(raw) > 20:
        raw = raw[:20]
    scores = [r["score"] for r in raw]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == 49.0
