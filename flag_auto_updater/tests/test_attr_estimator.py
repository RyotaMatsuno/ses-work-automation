from __future__ import annotations

from unittest.mock import patch

from attr_estimator import (
    estimate_nationality,
    estimate_nationality_llm,
    extract_residence_from_memo,
    is_alphabetic_dominant_name,
    is_clearly_japanese_name,
    is_id_code,
)


def test_is_id_code_patterns():
    assert is_id_code("BH0023") is True
    assert is_id_code("MY2057") is True
    assert is_id_code("No.0004") is True
    assert is_id_code("ID:17BZ766") is True
    assert is_id_code("N0788 CK") is True
    assert is_id_code("田中 太郎") is False
    assert is_id_code("H_T") is False


def test_id_code_skips_rule_based_nationality():
    value, reason = estimate_nationality("BH0023", "")
    assert value == "要確認"
    assert reason == "IDコード形式のため判定スキップ"


def test_estimate_nationality_llm_skips_id_code_without_calling_openai():
    with patch("attr_estimator._call_openai_nationality") as mock_call:
        value, reason = estimate_nationality_llm("BH0023", "最寄り: 渋谷")
    assert value == "要確認"
    assert reason == "判定材料なし"
    mock_call.assert_not_called()


@patch("attr_estimator._call_openai_nationality", return_value=("日本", "LLM判定: 日本"))
def test_estimate_nationality_llm_with_memo(mock_call):
    value, reason = estimate_nationality_llm("R.S", "最寄り: 渋谷駅、Java/Spring")
    assert value == "日本"
    assert reason == "LLM判定: 日本"
    mock_call.assert_called_once()


@patch("attr_estimator._call_openai_nationality", return_value=("外国籍候補", "LLM判定: 外国籍候補"))
def test_estimate_nationality_llm_foreign_from_memo(mock_call):
    value, reason = estimate_nationality_llm("R.S", "中国語ネイティブ、ベトナム在住歴あり")
    assert value == "外国籍候補"
    assert reason == "LLM判定: 外国籍候補"
    mock_call.assert_called_once()


def test_alphabetic_name_is_foreign_candidate():
    value, reason = estimate_nationality("John Smith", "")
    assert value == "外国籍候補"
    assert "アルファベット" in reason


def test_japanese_name_is_japan():
    value, reason = estimate_nationality("山田太郎", "")
    assert value == "日本"
    assert "日本語表記" in reason


def test_foreign_keyword_in_memo():
    value, reason = estimate_nationality("山田太郎", "中国語対応可能")
    assert value == "外国籍候補"
    assert "中国語" in reason


def test_weak_name_needs_review():
    value, reason = estimate_nationality("不明", "")
    assert value == "要確認"
    assert "判定できない" in reason


def test_initial_name_needs_review():
    value, _ = estimate_nationality("K.", "")
    assert value == "要確認"


def test_initials_default_to_japan():
    value, reason = estimate_nationality("R.S", "")
    assert value == "日本"
    assert "イニシャル" in reason


def test_initials_with_metadata_default_to_japan():
    value, _ = estimate_nationality("R.E（32歳/男性 Python/Django/AI 西船橋）", "")
    assert value == "日本"


def test_residence_from_station():
    value, reason = extract_residence_from_memo("最寄りは渋谷駅、リモート週2")
    assert value == "東京"
    assert "渋谷" in reason


def test_residence_unknown_when_no_station():
    value, reason = extract_residence_from_memo("面談調整中")
    assert value is None
    assert reason is None


def test_regional_station_maps_to_prefecture():
    value, reason = extract_residence_from_memo("大阪在住、週1出社")
    assert value == "大阪"
    assert "大阪" in reason


def test_name_helpers():
    assert is_alphabetic_dominant_name("John Smith") is True
    assert is_clearly_japanese_name("タナカ タロウ") is True
    assert is_clearly_japanese_name("John Smith") is False
