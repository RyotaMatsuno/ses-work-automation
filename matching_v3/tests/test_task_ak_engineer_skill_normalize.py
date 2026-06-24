from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from matcher import SkillNormalizer

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
SPEC = importlib.util.spec_from_file_location(
    "normalize_engineer_skills",
    SCRIPTS_DIR / "normalize_engineer_skills.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


def _normalizer() -> SkillNormalizer:
    return SkillNormalizer(Path(__file__).resolve().parents[1] / "skill_aliases.json")


def test_normalize_skills_splits_and_canonicalizes():
    normalizer = _normalizer()
    raw = ["java", "JAVA", "unknown-skill"]
    canonical, mapping = mod.normalize_skills(raw, normalizer)

    assert "Java" in canonical
    assert len(mapping) == 3
    assert mapping[0]["canonical"] == "Java"


def test_coverage_stats_counts_alias_hits():
    normalizer = _normalizer()
    stats = mod.coverage_stats(["java", "xyz-not-in-dict"], normalizer)

    assert stats["total"] == 2
    assert stats["covered"] == 1
    assert stats["coverage_pct"] == 50.0


def test_normalize_skills_dedupes_aliases():
    normalizer = _normalizer()
    canonical, _ = mod.normalize_skills(["java", "JAVA", "Java"], normalizer)

    assert canonical == ["Java"]


def test_judge_prefers_normalized_skills_field():
    from matcher import SkillNormalizer, judge_with_meta

    normalizer = _normalizer()
    case = {"required_skills": ["Java"], "price_max": 72}
    engineer = {
        "スキル": ["Python"],
        "正規化スキル": ["Java"],
        "単価（万円）": 60,
    }
    result = judge_with_meta(case, engineer, normalizer)

    assert result["verdict"] in ("MATCH", "REVIEW")
