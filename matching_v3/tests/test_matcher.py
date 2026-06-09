from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from matcher import SkillNormalizer, _calc_parallel_score, judge


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
    assert reasons == ["粗利不足: -20.0万円 < 5万円"]


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
    assert reasons == ["粗利不足: 4.0万円 < 5万円"]


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
    assert reasons == ["粗利不足: 2.0万円 < 3万円"]


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


def test_parallel_score_result_waiting_over_15_days():
    engineer = _engineer_result_waiting("2026-06-20")

    score = _calc_parallel_score(engineer, today=date(2026, 7, 6))

    assert score == 1.0


def test_parallel_score_result_waiting_without_interview_date():
    engineer = _engineer_result_waiting(None)

    score = _calc_parallel_score(engineer, today=date(2026, 6, 22))

    assert score == 1.0
