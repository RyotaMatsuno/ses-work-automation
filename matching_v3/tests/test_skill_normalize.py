"""test_skill_normalize.py — スキル正規化テスト (Phase 2A2)"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from matcher import SkillNormalizer, canonicalize_skill_list

_ALIASES_PATH = ROOT / "skill_aliases.json"


@pytest.fixture(scope="module")
def normalizer() -> SkillNormalizer:
    return SkillNormalizer(_ALIASES_PATH)


def test_normalize_basic(normalizer: SkillNormalizer) -> None:
    """Java → Java、React.js → React に正規化される。"""
    assert normalizer.resolve_canonical("java") == "Java"
    assert normalizer.resolve_canonical("Java") == "Java"
    assert normalizer.resolve_canonical("React.js") == "React"
    assert normalizer.resolve_canonical("react.js") == "React"


def test_normalize_unknown_preserved(normalizer: SkillNormalizer) -> None:
    """未知スキルは canonicalize_skill_list 経由でそのまま保持される。"""
    unknown = "超絶レアスキルXYZ_未登録"
    result = canonicalize_skill_list([unknown], normalizer)
    assert result == [unknown]


def test_normalize_empty_skills(normalizer: SkillNormalizer) -> None:
    """スキルなしエンジニアは空リストを返す。"""
    result = canonicalize_skill_list([], normalizer)
    assert result == []
