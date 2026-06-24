from __future__ import annotations

from datetime import date, timedelta

from rule_engine import BLANK_DAYS_THRESHOLD, format_reasons, judge_engineer

TODAY = date(2026, 6, 9)


def _engineer(**overrides) -> dict:
    base = {
        "名前": "テスト太郎",
        "properties": {
            "国籍": "日本",
            "居住地": "東京",
            "稼働終了日": None,
            "短期連続フラグ": False,
            "既往歴フラグ": False,
        },
    }
    base["properties"].update(overrides)
    return base


def test_foreign_nationality_excluded():
    engineer = _engineer(国籍="アメリカ")
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is False
    assert reasons == ["外国籍"]


def test_regional_engineer_excluded():
    engineer = _engineer(居住地="大阪")
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is False
    assert reasons == ["地方人材: 大阪"]


def test_blank_within_threshold_is_target():
    end_date = (TODAY - timedelta(days=30)).isoformat()
    engineer = _engineer(稼働終了日=end_date)
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is True
    assert reasons == []


def test_blank_over_threshold_excluded():
    end_date = (TODAY - timedelta(days=BLANK_DAYS_THRESHOLD + 1)).isoformat()
    engineer = _engineer(稼働終了日=end_date)
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is False
    assert reasons == [f"ブランク{BLANK_DAYS_THRESHOLD + 1}日"]


def test_short_term_flag_excluded():
    engineer = _engineer(短期連続フラグ=True)
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is False
    assert reasons == ["短期案件連続"]


def test_history_flag_excluded():
    engineer = _engineer(既往歴フラグ=True)
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is False
    assert reasons == ["既往歴"]


def test_all_clear_is_target():
    engineer = _engineer()
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is True
    assert reasons == []


def test_multiple_exclusion_reasons():
    engineer = _engineer(国籍="ベトナム", 居住地="大阪", 短期連続フラグ=True)
    is_target, reasons = judge_engineer(engineer, today=TODAY)
    assert is_target is False
    assert reasons == ["外国籍", "地方人材: 大阪", "短期案件連続"]
    assert format_reasons(reasons) == "外国籍\n地方人材: 大阪\n短期案件連続"
