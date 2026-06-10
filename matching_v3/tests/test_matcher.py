from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from matcher import (
    SkillNormalizer,
    _calc_parallel_score,
    calc_gross_profit,
    filter_fresh_engineers,
    is_engineer_fresh,
    judge,
    meets_profit_floor,
)


def _normalizer():
    return SkillNormalizer("skill_aliases.json")


def test_ng_price_exceeded():
    case = {"required_skills": [], "price_max": 50, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 80, "スキル": []}

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "NG"
    assert "粗利不足" in reasons[0]


def test_ng_required_skill_missing():
    case = {"required_skills": ["Java"], "price_max": 100, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 60, "スキル": ["Python"]}

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "NG"
    assert "必須スキル不足" in reasons[0]


def test_match_all_required_skills_and_low_parallel_score():
    case = {"required_skills": ["Java", "Spring"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = {
        "単価（万円）": 70,
        "スキル": ["Java", "Spring"],
        "備考（LINEメモ）": "面談調整中",
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert reasons == []


def test_ng_when_only_ambiguous_skills_exist():
    case = {
        "required_skills": ["Java"],
        "ambiguous_skills": ["クラウド経験"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = {"単価（万円）": 70, "スキル": ["Java"], "_last_edited_time": datetime.now(timezone.utc).isoformat()}

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "NG"
    assert reasons == ["曖昧スキルのみ: 判定不可"]


def test_ng_when_case_price_is_estimated_below_gross_floor():
    case = {"required_skills": ["Java"], "price_max": None, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 70, "スキル": ["Java"], "_last_edited_time": datetime.now(timezone.utc).isoformat()}

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "NG"
    assert reasons == ["粗利不足: -20.0万円 < 最低粗利5万円"]


def test_engineer_skills_are_normalized_before_matching():
    case = {"required_skills": ["Spring Boot"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 70, "スキル": ["SpringBoot"], "_last_edited_time": datetime.now(timezone.utc).isoformat()}

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert reasons == []


def test_review_when_engineer_data_is_22_days_old():
    case = {"required_skills": ["Java"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = {
        "単価（万円）": 70,
        "スキル": ["Java"],
        "_last_edited_time": (datetime.now(timezone.utc) - timedelta(days=22)).isoformat(),
    }

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "REVIEW"
    assert any("エンジニア情報古い" in reason for reason in reasons)


def test_skill_normalizer_converts_js_alias():
    assert _normalizer().normalize("JS") == "JavaScript"


def test_ng_gross_below_matsuno_floor():
    case = {"required_skills": [], "price_max": 74, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 70, "スキル": []}

    verdict, reasons = judge(case, engineer, _normalizer(), assignee="松野")

    assert verdict == "NG"
    assert reasons == ["粗利不足: 4.0万円 < 最低粗利5万円"]


def test_match_gross_at_matsuno_floor():
    case = {"required_skills": [], "price_max": 75, "extraction_confidence": 1.0}
    engineer = {
        "単価（万円）": 70,
        "スキル": [],
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }

    verdict, reasons = judge(case, engineer, _normalizer(), assignee="松野")

    assert verdict == "MATCH"
    assert reasons == []


def test_match_gross_above_okamoto_floor():
    case = {"required_skills": [], "price_max": 73, "extraction_confidence": 1.0}
    engineer = {
        "単価（万円）": 70,
        "スキル": [],
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }

    verdict, reasons = judge(case, engineer, _normalizer(), assignee="岡本")

    assert verdict == "MATCH"
    assert reasons == []


def test_ng_gross_below_okamoto_floor():
    case = {"required_skills": [], "price_max": 72, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 70, "スキル": []}

    verdict, reasons = judge(case, engineer, _normalizer(), assignee="岡本")

    assert verdict == "NG"
    assert reasons == ["粗利不足: 2.0万円 < 最低粗利3万円"]


def _engineer_result_waiting(interview_date: str | None) -> dict:
    parallel = {"ステータス": "結果待ち"}
    if interview_date is not None:
        parallel["面談日"] = interview_date
    return {"並行案件": [parallel]}


def test_parallel_score_result_waiting_2_days():
    engineer = _engineer_result_waiting("2026-06-20")

    score = _calc_parallel_score(engineer, today=date(2026, 6, 22))

    assert score == 2.5


def test_parallel_score_result_waiting_5_days():
    engineer = _engineer_result_waiting("2026-06-20")

    score = _calc_parallel_score(engineer, today=date(2026, 6, 25))

    assert score == 2.0


def test_parallel_score_result_waiting_8_days_not_counted():
    engineer = _engineer_result_waiting("2026-06-20")

    score = _calc_parallel_score(engineer, today=date(2026, 6, 28))

    assert score == 0.0


def test_gross_profit_70_60_is_match():
    case = {"required_skills": [], "price_max": 70, "extraction_confidence": 1.0}
    engineer = {
        "単価（万円）": 60,
        "スキル": [],
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert calc_gross_profit(70, 60) == 10.0
    assert meets_profit_floor(70, 60)


def test_gross_profit_60_56_is_ng():
    case = {"required_skills": [], "price_max": 60, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 56, "スキル": []}

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "NG"
    assert reasons == ["粗利不足: 4.0万円 < 最低粗利5万円"]


def test_gross_profit_60_55_borderline_is_match():
    case = {"required_skills": [], "price_max": 60, "extraction_confidence": 1.0}
    engineer = {
        "単価（万円）": 55,
        "スキル": [],
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert meets_profit_floor(60, 55)


def test_gross_profit_okamoto_50_48_is_ng():
    case = {"required_skills": [], "price_max": 50, "extraction_confidence": 1.0}
    engineer = {"単価（万円）": 48, "スキル": []}

    verdict, reasons = judge(case, engineer, _normalizer(), assignee="岡本")

    assert verdict == "NG"
    assert reasons == ["粗利不足: 2.0万円 < 最低粗利3万円"]


def test_gross_profit_okamoto_50_47_is_match():
    case = {"required_skills": [], "price_max": 50, "extraction_confidence": 1.0}
    engineer = {
        "単価（万円）": 47,
        "スキル": [],
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }

    verdict, reasons = judge(case, engineer, _normalizer(), assignee="岡本")

    assert verdict == "MATCH"
    assert meets_profit_floor(50, 47, floor_man=3.0)


def test_is_engineer_fresh_20_days_old():
    engineer = {
        "名前": "新鮮太郎",
        "_last_edited_time": (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(),
    }

    assert is_engineer_fresh(engineer) is True


def test_is_engineer_fresh_22_days_old():
    engineer = {
        "名前": "古い太郎",
        "_last_edited_time": (datetime.now(timezone.utc) - timedelta(days=22)).isoformat(),
    }

    assert is_engineer_fresh(engineer) is False


def test_is_engineer_fresh_boundary_exactly_21days():
    """21日ちょうどは提案対象に含まれること"""
    exactly_21 = (datetime.now(timezone.utc) - timedelta(days=21)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    engineer = {"_last_edited_time": exactly_21}
    assert is_engineer_fresh(engineer) is True


def test_is_engineer_fresh_boundary_22days():
    """22日前は提案対象外"""
    twenty_two = (datetime.now(timezone.utc) - timedelta(days=22)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )
    engineer = {"_last_edited_time": twenty_two}
    assert is_engineer_fresh(engineer) is False


def test_is_engineer_fresh_missing_last_updated():
    assert is_engineer_fresh({"名前": "不明太郎"}) is False


def test_is_engineer_fresh_prefers_last_updated_field():
    engineer = {
        "最終更新日": datetime.now(timezone.utc).isoformat(),
        "_last_edited_time": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
    }

    assert is_engineer_fresh(engineer) is True


def test_filter_fresh_engineers_excludes_stale_and_logs(caplog):
    import logging

    fresh_time = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat()
    stale_time = (datetime.now(timezone.utc) - timedelta(days=22)).isoformat()
    engineers = [
        {"id": "fresh", "名前": "新鮮", "_last_edited_time": fresh_time},
        {"id": "stale", "名前": "古い", "_last_edited_time": stale_time},
        {"id": "unknown", "名前": "不明"},
    ]

    with caplog.at_level(logging.INFO):
        result = filter_fresh_engineers(engineers)

    assert [item["id"] for item in result] == ["fresh"]
    assert "stale: 古い (22日経過)" in caplog.text
    assert "stale: 不明 (最終更新日不明)" in caplog.text


def test_parallel_score_result_waiting_without_interview_date():
    engineer = _engineer_result_waiting(None)

    score = _calc_parallel_score(engineer, today=date(2026, 6, 22))

    assert score == 1.0
