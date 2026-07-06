"""test_delete_zero_ref_canonicals.py — delete_zero_ref_canonicals.py のユニットテスト。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
for p in (str(ROOT), str(TOOLS_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from delete_zero_ref_canonicals import _validate, run_delete


# ── フィクスチャ ────────────────────────────────────────────────


def _make_aliases_json(
    canonicals: list[str],
    aliases: dict[str, str],
    tmp_path: Path,
    soft_aliases: dict[str, str] | None = None,
) -> Path:
    data = {
        "version": "test",
        "generated": "2026-07-07",
        "source": "test",
        "normalize_rule": "lowercase",
        "canonical_skills": canonicals,
        "aliases": aliases,
        "soft_aliases": soft_aliases or {},
        "soft_aliases_enabled": False,
        "strict_alias_keys": [],
        "parent_skills": {},
        "skill_tiers": {},
        "notes": "",
    }
    p = tmp_path / "skill_aliases.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _make_empty_engineers(tmp_path: Path) -> Path:
    p = tmp_path / "poc_engineers.json"
    p.write_text("[]", encoding="utf-8")
    return p


def _make_empty_structured(tmp_path: Path) -> Path:
    p = tmp_path / "structured.jsonl"
    p.write_text("", encoding="utf-8")
    return p


# ── テスト ────────────────────────────────────────────────────


def test_zero_ref_canonical_is_deleted(tmp_path: pytest.TempPathFactory) -> None:
    """参照0のcanonicalが削除されること。"""
    canonicals = ["Ad-hoc", "Python", "Java"]
    aliases = {
        "ad-hoc": "Ad-hoc",
        "adhoc": "Ad-hoc",
        "python": "Python",
        "java": "Java",
    }
    aliases_path = _make_aliases_json(canonicals, aliases, tmp_path)
    eng_path = _make_empty_engineers(tmp_path)
    structured_path = _make_empty_structured(tmp_path)

    result = run_delete(
        aliases_path=aliases_path,
        engineers_path=eng_path,
        structured_path=structured_path,
        dry_run=True,
    )

    assert "Ad-hoc" in result["deleted"]
    data = json.loads(aliases_path.read_text(encoding="utf-8"))
    # dry_run=True なのでファイルは変更されない
    assert "Ad-hoc" in data["canonical_skills"]


def test_zero_ref_canonical_deleted_in_live_run(tmp_path: pytest.TempPathFactory) -> None:
    """dry_run=False でファイルが実際に更新されること。"""
    canonicals = ["Ad-hoc", "Python", "Java"]
    aliases = {
        "ad-hoc": "Ad-hoc",
        "adhoc": "Ad-hoc",
        "python": "Python",
        "java": "Java",
    }
    aliases_path = _make_aliases_json(canonicals, aliases, tmp_path)
    eng_path = _make_empty_engineers(tmp_path)
    structured_path = _make_empty_structured(tmp_path)

    result = run_delete(
        aliases_path=aliases_path,
        engineers_path=eng_path,
        structured_path=structured_path,
        dry_run=False,
    )

    assert "Ad-hoc" in result["deleted"]
    data = json.loads(aliases_path.read_text(encoding="utf-8"))
    assert "Ad-hoc" not in data["canonical_skills"]
    assert "ad-hoc" not in data["aliases"]
    assert "adhoc" not in data["aliases"]
    assert result["aliases_removed"] == 2


def test_nonzero_ref_canonical_is_skipped(tmp_path: pytest.TempPathFactory) -> None:
    """参照>0のcanonicalがスキップされること。"""
    canonicals = ["DBA", "Python"]
    aliases = {
        "dba": "DBA",
        "python": "Python",
    }
    aliases_path = _make_aliases_json(canonicals, aliases, tmp_path)
    eng_path = _make_empty_engineers(tmp_path)

    # structured.jsonl に DBA を含む案件を1件追加
    structured_path = tmp_path / "structured.jsonl"
    row = {"required_skills": ["DBA"], "optional_skills": [], "ambiguous_skills": []}
    structured_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

    result = run_delete(
        aliases_path=aliases_path,
        engineers_path=eng_path,
        structured_path=structured_path,
        dry_run=True,
    )

    # DBA は参照ありなのでスキップ
    skipped_names = [s["canonical"] for s in result["skipped_with_reason"]]
    assert "DBA" in skipped_names
    assert "DBA" not in result["deleted"]


def test_no_dangling_aliases_after_deletion(tmp_path: pytest.TempPathFactory) -> None:
    """削除後のJSONにdangling alias（存在しないcanonicalを指すalias）が無いこと。"""
    canonicals = ["ログ", "Python"]
    aliases = {
        "log": "ログ",
        "ログ": "ログ",
        "python": "Python",
    }
    aliases_path = _make_aliases_json(canonicals, aliases, tmp_path)
    eng_path = _make_empty_engineers(tmp_path)
    structured_path = _make_empty_structured(tmp_path)

    result = run_delete(
        aliases_path=aliases_path,
        engineers_path=eng_path,
        structured_path=structured_path,
        dry_run=False,
    )

    assert "ログ" in result["deleted"]
    data = json.loads(aliases_path.read_text(encoding="utf-8"))
    canonical_set = set(data["canonical_skills"])

    # aliases に dangling がないこと
    for k, v in data["aliases"].items():
        assert v in canonical_set, f"dangling alias: {k!r} -> {v!r}"
    for k, v in data["soft_aliases"].items():
        assert v in canonical_set, f"dangling soft_alias: {k!r} -> {v!r}"


def test_validate_raises_on_wrong_count() -> None:
    """検証関数が件数不整合で AssertionError を送出すること。"""
    with pytest.raises(AssertionError, match="canonical件数不整合"):
        _validate(
            new_canonicals=["Python"],  # 実際は1件 (count_after=1)
            new_aliases={"python": "Python"},
            new_soft={},
            count_before=10,
            count_after=1,
            deleted_count=5,  # 10 - 5 = 5 のはずなので count_after=1 と不整合
        )


def test_validate_raises_on_dangling_alias() -> None:
    """検証関数がdangling aliasで AssertionError を送出すること。"""
    with pytest.raises(AssertionError, match="dangling alias"):
        _validate(
            new_canonicals=["Python"],
            new_aliases={"java": "Java"},  # Java は canonicals にない
            new_soft={},
            count_before=2,
            count_after=1,  # 2 - 1 = 1 なので件数は合う
            deleted_count=1,
        )
