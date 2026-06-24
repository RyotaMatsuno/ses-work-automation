from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mail_pipeline.validation import (
    append_remark,
    missing_engineer_properties,
    normalize_price_yen,
    validate_engineer,
)


def test_skip_when_name_missing():
    result = validate_engineer({"name": "", "skills": ["Java"], "price": 60})

    assert result.status == "SKIP"
    assert "氏名欠損" in result.reasons


def test_review_when_skills_missing():
    result = validate_engineer({"name": "山田太郎", "skills": [], "price": 60, "available_date": "2026-07-01"})

    assert result.status == "REVIEW"
    assert "スキル欠損" in result.reasons
    assert result.proposal_target is False


def test_review_when_start_date_missing_or_vague():
    for value in ("", "即日", "応相談", "確認中"):
        result = validate_engineer({"name": "山田太郎", "skills": ["Java"], "price": 60, "available_date": value})
        assert result.status == "REVIEW"
        assert any("稼働開始日" in reason for reason in result.reasons)


def test_foreign_nationality_sets_proposal_target_false():
    result = validate_engineer(
        {
            "name": "Y.T",
            "skills": ["Java"],
            "price": 60,
            "available_date": "2026-07-01",
            "note": "外国籍候補のエンジニアです",
        }
    )

    assert result.proposal_target is False
    assert any("外国籍" in reason for reason in result.reasons)


def test_non_kanto_sets_proposal_target_false():
    result = validate_engineer(
        {
            "name": "大阪太郎",
            "skills": ["Java"],
            "price": 60,
            "available_date": "2026-07-01",
            "location": "大阪府在住",
        }
    )

    assert result.proposal_target is False
    assert any("関東圏外" in reason for reason in result.reasons)


def test_non_kanto_with_exception_stays_review_only():
    result = validate_engineer(
        {
            "name": "大阪太郎",
            "skills": ["Java"],
            "price": 60,
            "available_date": "2026-07-01",
            "location": "大阪府在住・フルリモート可",
        }
    )

    assert result.proposal_target is True
    assert result.status == "REVIEW"
    assert any("例外条件あり" in reason for reason in result.reasons)


def test_price_normalization_and_review_cases():
    assert normalize_price_yen("50万") == 500_000
    assert normalize_price_yen("50〜55万") == 500_000

    for price in (None, 0, -1, "応相談"):
        result = validate_engineer(
            {
                "name": "山田太郎",
                "skills": ["Java"],
                "price": price,
                "available_date": "2026-07-01",
            }
        )
        assert result.status == "REVIEW"
        assert "単価要確認" in result.reasons


def test_multiple_reasons_collected():
    result = validate_engineer(
        {
            "name": "山田太郎",
            "skills": [],
            "price": "応相談",
            "available_date": "即日",
            "note": "外国籍",
            "location": "愛知県",
        }
    )

    assert result.status == "REVIEW"
    assert len(result.reasons) >= 3
    assert result.proposal_target is False


def test_skip_priority_over_review():
    result = validate_engineer(
        {
            "name": "",
            "skills": [],
            "price": None,
            "note": "外国籍",
        }
    )

    assert result.status == "SKIP"


def test_append_remark_keeps_existing_text():
    merged = append_remark("既存メモ", ["[validation] 単価要確認"])

    assert merged.startswith("既存メモ")
    assert merged.endswith("[validation] 単価要確認")


def test_missing_engineer_properties_detects_absence():
    props = {"名前", "スキル", "単価（万円）", "備考（LINEメモ）", "提案対象フラグ", "稼働可能日"}

    missing = missing_engineer_properties(props)

    assert "情報取得日" in missing
