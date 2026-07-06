from __future__ import annotations

from pathlib import Path

import pytest

from matcher import SkillNormalizer, normalize_skill_with_log, unique_skill_count_report
from skill_judge import skills_must_not_merge

BASE = Path(__file__).resolve().parents[1]


@pytest.fixture
def normalizer() -> SkillNormalizer:
    return SkillNormalizer(BASE / "skill_aliases.json")


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("Java", "JavaScript"),
        ("C", "C#"),
        ("C", "C++"),
        ("C#", "C++"),
        ("SQL", "MySQL"),
        ("SQL", "PostgreSQL"),
        ("MySQL", "PostgreSQL"),
    ],
)
def test_must_not_merge_pairs(left: str, right: str):
    assert skills_must_not_merge(left, right) is True
    assert normalize_skill_with_log(left, SkillNormalizer(BASE / "skill_aliases.json"))["normalized_skill"] != (
        normalize_skill_with_log(right, SkillNormalizer(BASE / "skill_aliases.json"))["normalized_skill"]
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mysql8", "MySQL"),
        ("python3", "Python"),
        ("java 17", "Java"),
        ("node 20", "Node.js"),
        ("vue 3", "Vue.js"),
        ("react 18", "React"),
        ("docker compose", "Docker"),
        ("terraform cloud", "Terraform"),
    ],
)
def test_phase6_high_frequency_aliases(normalizer: SkillNormalizer, raw: str, expected: str):
    entry = normalize_skill_with_log(raw, normalizer)
    assert entry["normalized_skill"] == expected
    assert entry["rule_hit"] == "hard_alias"


def test_unique_skill_count_report(normalizer: SkillNormalizer):
    raw = ["java 17", "Java", "python3", "Python", "mysql8", "MySQL"]
    report = unique_skill_count_report(raw, normalizer)
    assert report["raw_unique_count"] == 6
    assert report["normalized_unique_count"] == 3
