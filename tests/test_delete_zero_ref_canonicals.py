"""tests/test_delete_zero_ref_canonicals.py — delete_zero_ref_canonicals.py のテスト"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "matching_v3" / "tools"))
import delete_zero_ref_canonicals as dz
from delete_zero_ref_canonicals import (
    TARGET_CANONICALS,
    _parse_zero_ref_from_audit,
    run_delete,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_aliases_json(path: Path, canonicals: list[str] | None = None) -> None:
    """テスト用の最小 skill_aliases.json を作成する。"""
    if canonicals is None:
        canonicals = sorted(TARGET_CANONICALS) + ["Python", "Java"]
    data = {
        "canonical_skills": canonicals,
        "aliases": {c: c for c in canonicals[:3]},
        "soft_aliases": {f"soft_{c}": c for c in canonicals[:2]},
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_audit_report(path: Path, zero_refs: frozenset[str] | None = None) -> None:
    """TARGET_CANONICALSと一致する最小監査レポートを作成する。"""
    if zero_refs is None:
        zero_refs = TARGET_CANONICALS
    lines = [
        "# canonical_skills ゴミ混入 dry-run 調査レポート",
        "",
        "## dummy section",
        "",
        "| canonical | 判定理由 | 人材参照 | 案件参照 | 合計 | 削除影響見立て | エイリアス数 |",
        "|-----------|----------|----------|----------|------|----------------|-------------|",
    ]
    for c in sorted(zero_refs):
        lines.append(f"| {c} | テスト | 0 | 0 | 0 | 影響なし | 1 |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _mock_normalizer() -> MagicMock:
    m = MagicMock()
    m.resolve_canonical.return_value = None  # 全トークンが参照0
    return m


# ---------------------------------------------------------------------------
# dry-run デフォルト: ファイルが変更されないこと
# ---------------------------------------------------------------------------

def test_dry_run_default_does_not_modify_file(tmp_path):
    aliases_path = tmp_path / "skill_aliases.json"
    audit_path = tmp_path / "audit.md"
    _make_aliases_json(aliases_path)
    _make_audit_report(audit_path)
    original_text = aliases_path.read_text(encoding="utf-8")

    with patch.object(dz, "_load_normalizer", return_value=_mock_normalizer()):
        run_delete(
            aliases_path=aliases_path,
            engineers_path=tmp_path / "engineers.json",
            structured_path=tmp_path / "structured.jsonl",
            audit_report_path=audit_path,
            dry_run=True,  # デフォルト
        )

    assert aliases_path.read_text(encoding="utf-8") == original_text, (
        "dry_run=True のとき skill_aliases.json を書き換えてはならない"
    )


# ---------------------------------------------------------------------------
# --execute: 書き込みが発生すること
# ---------------------------------------------------------------------------

def test_execute_modifies_file(tmp_path):
    aliases_path = tmp_path / "skill_aliases.json"
    audit_path = tmp_path / "audit.md"
    _make_aliases_json(aliases_path)
    _make_audit_report(audit_path)
    original_data = json.loads(aliases_path.read_text(encoding="utf-8"))

    with patch.object(dz, "_load_normalizer", return_value=_mock_normalizer()):
        result = run_delete(
            aliases_path=aliases_path,
            engineers_path=tmp_path / "engineers.json",
            structured_path=tmp_path / "structured.jsonl",
            audit_report_path=audit_path,
            dry_run=False,
        )

    new_data = json.loads(aliases_path.read_text(encoding="utf-8"))
    assert len(new_data["canonical_skills"]) < len(original_data["canonical_skills"]), (
        "dry_run=False のとき canonical_skills が削減されなければならない"
    )
    assert len(result["deleted"]) > 0
    assert "soft_aliases_removed" in result, "結果dictに soft_aliases_removed が含まれること"
    assert "force_skip_audit_used" in result, "結果dictに force_skip_audit_used が含まれること"
    assert result["force_skip_audit_used"] is False


# ---------------------------------------------------------------------------
# バックアップ名に時刻が含まれること
# ---------------------------------------------------------------------------

def test_backup_name_includes_timestamp(tmp_path):
    aliases_path = tmp_path / "skill_aliases.json"
    audit_path = tmp_path / "audit.md"
    _make_aliases_json(aliases_path)
    _make_audit_report(audit_path)

    with patch.object(dz, "_load_normalizer", return_value=_mock_normalizer()):
        run_delete(
            aliases_path=aliases_path,
            engineers_path=tmp_path / "engineers.json",
            structured_path=tmp_path / "structured.jsonl",
            audit_report_path=audit_path,
            dry_run=False,
        )

    bak_files = list(tmp_path.glob("skill_aliases.json.bak_canonical38_*"))
    assert len(bak_files) == 1, "バックアップファイルが1件作成されること"
    # YYYYMMDD_HHMMSS 形式であることを確認
    assert re.search(r"bak_canonical38_\d{8}_\d{6}$", bak_files[0].name), (
        f"バックアップ名に YYYYMMDD_HHMMSS が含まれること: {bak_files[0].name}"
    )


# ---------------------------------------------------------------------------
# 監査レポート不一致: 中断すること
# ---------------------------------------------------------------------------

def test_audit_mismatch_raises(tmp_path):
    aliases_path = tmp_path / "skill_aliases.json"
    audit_path = tmp_path / "audit.md"
    _make_aliases_json(aliases_path)
    # TARGET_CANONICALSに含まれない別のcanonicalをレポートに入れる
    wrong_zeros = frozenset(["NonExistentSkill", "AnotherFake"])
    _make_audit_report(audit_path, zero_refs=wrong_zeros)
    original_text = aliases_path.read_text(encoding="utf-8")

    with patch.object(dz, "_load_normalizer", return_value=_mock_normalizer()):
        with pytest.raises(ValueError, match="一致しません"):
            run_delete(
                aliases_path=aliases_path,
                engineers_path=tmp_path / "engineers.json",
                structured_path=tmp_path / "structured.jsonl",
                audit_report_path=audit_path,
                dry_run=False,
                force_skip_audit=False,
            )

    # ファイルは変更されていないこと（バックアップも作成されていない）
    assert aliases_path.read_text(encoding="utf-8") == original_text
    assert list(tmp_path.glob("*.bak_*")) == []


def test_audit_report_missing_raises(tmp_path):
    aliases_path = tmp_path / "skill_aliases.json"
    _make_aliases_json(aliases_path)

    with patch.object(dz, "_load_normalizer", return_value=_mock_normalizer()):
        with pytest.raises(FileNotFoundError, match="監査レポートが見つかりません"):
            run_delete(
                aliases_path=aliases_path,
                engineers_path=tmp_path / "engineers.json",
                structured_path=tmp_path / "structured.jsonl",
                audit_report_path=tmp_path / "nonexistent_audit.md",
                dry_run=False,
                force_skip_audit=False,
            )


def test_force_skip_audit_bypasses_missing_report(tmp_path):
    aliases_path = tmp_path / "skill_aliases.json"
    _make_aliases_json(aliases_path)

    with patch.object(dz, "_load_normalizer", return_value=_mock_normalizer()):
        result = run_delete(
            aliases_path=aliases_path,
            engineers_path=tmp_path / "engineers.json",
            structured_path=tmp_path / "structured.jsonl",
            audit_report_path=tmp_path / "nonexistent_audit.md",
            dry_run=True,
            force_skip_audit=True,
        )
    assert "deleted" in result


# ---------------------------------------------------------------------------
# _parse_zero_ref_from_audit: パーサー単体テスト
# ---------------------------------------------------------------------------

def test_parse_zero_ref_from_audit(tmp_path):
    audit_path = tmp_path / "audit.md"
    expected = frozenset(["Python", "Java"])
    lines = [
        "| canonical | 判定理由 | 人材参照 | 案件参照 | 合計 | 削除影響見立て | エイリアス数 |",
        "|-----------|----------|----------|----------|------|----------------|-------------|",
        "| Python | テスト | 0 | 0 | 0 | 影響なし | 1 |",
        "| Java | テスト | 0 | 0 | 0 | 影響なし | 1 |",
        "| AWS | テスト | 3 | 5 | 8 | 影響あり | 2 |",  # 参照あり→対象外
    ]
    audit_path.write_text("\n".join(lines), encoding="utf-8")
    result = _parse_zero_ref_from_audit(audit_path)
    assert result == expected
