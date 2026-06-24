from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from matcher import (
    SkillNormalizer,
    _calc_parallel_score,
    _extract_result_wait_days,
    _is_process_skill,
    _result_wait_score,
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
    engineer = {
        "単価（万円）": 70,
        "スキル": ["SpringBoot"],
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }

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

    assert verdict == "MATCH"
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
    exactly_21 = (datetime.now(timezone.utc) - timedelta(days=21)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    engineer = {"_last_edited_time": exactly_21}
    assert is_engineer_fresh(engineer) is True


def test_is_engineer_fresh_boundary_22days():
    """22日前は提案対象外"""
    twenty_two = (datetime.now(timezone.utc) - timedelta(days=22)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    engineer = {"_last_edited_time": twenty_two}
    assert is_engineer_fresh(engineer) is False


def test_is_engineer_fresh_missing_last_updated():
    assert is_engineer_fresh({"名前": "不明太郎"}) is False


def test_is_engineer_fresh_prefers_info_acquired_date():
    engineer = {
        "情報取得日": (datetime.now(timezone.utc) - timedelta(days=5)).date().isoformat(),
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


def test_memo_result_waiting_1_day_ago():
    engineer = {"備考（LINEメモ）": "結果待ち 6/18"}

    score = _calc_parallel_score(engineer, today=date(2026, 6, 19))

    assert score == 2.5


def test_memo_result_waiting_4_days_ago():
    engineer = {"備考（LINEメモ）": "結果待ち 6/15"}

    score = _calc_parallel_score(engineer, today=date(2026, 6, 19))

    assert score == 2.0


def test_memo_result_waiting_18_days_ago_not_counted():
    engineer = {"備考（LINEメモ）": "結果待ち 6/1"}

    score = _calc_parallel_score(engineer, today=date(2026, 6, 19))

    assert score == 0.0


def test_memo_result_waiting_without_date_defaults_to_2():
    engineer = {"備考（LINEメモ）": "結果待ち"}

    score = _calc_parallel_score(engineer, today=date(2026, 6, 19))

    assert score == 2.0


def test_extract_result_wait_days_with_month_kanji():
    assert _extract_result_wait_days("結果待ち（6月15日）", today=date(2026, 6, 19)) == 4


def test_result_wait_score_none_defaults_to_2():
    assert _result_wait_score(None) == 2.0


def _fresh_engineer(**overrides):
    base = {
        "単価（万円）": 70,
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


def test_review_when_required_skill_is_unknown_vocab():
    # OpenShift は辞書外スキル
    case = {"required_skills": ["OpenShift"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "REVIEW"
    assert any("語彙外必須スキル要確認: OpenShift" in reason for reason in reasons)


def test_review_when_known_skill_matches_and_unknown_skill_present():
    # OpenShift は辞書外スキル
    case = {"required_skills": ["Java", "OpenShift"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "REVIEW"
    assert any("語彙外必須スキル要確認: OpenShift" in reason for reason in reasons)
    assert not any("必須スキル不足" in reason for reason in reasons)


def test_review_when_all_required_skills_are_unknown_vocab():
    # OpenShift / Maximo は辞書外スキル
    case = {"required_skills": ["OpenShift", "Maximo"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "REVIEW"
    assert any("語彙外必須スキル要確認" in reason for reason in reasons)
    assert "OpenShift" in reasons[0]
    assert "Maximo" in reasons[0]


def test_match_when_required_skill_is_soft_skill_only():
    case = {"required_skills": ["PM経験"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert reasons == []


def test_match_when_ambiguous_skill_is_soft_skill():
    case = {
        "required_skills": ["Java"],
        "ambiguous_skills": ["コミュニケーション力"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert not any("曖昧スキルあり" in reason for reason in reasons)


def test_match_when_unknown_skill_has_evidence_in_raw_skills():
    """語彙外スキルでもエンジニアの生スキルにfuzzy一致すればMATCH"""
    # OpenShift は辞書外だが生スキルリストに存在
    case = {"required_skills": ["OpenShift"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["OpenShift"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert not any("語彙外必須スキル要確認" in r for r in reasons)


def test_match_when_unknown_ratio_below_30_percent():
    """語彙外スキル(証拠なし)が30%以下の場合はMATCH"""
    case = {
        "required_skills": ["Java", "Python", "AWS", "OpenShift"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    # Java/Python/AWSは辞書にあり、OpenShiftは辞書外・証拠なし (1/4=25%≤30%)
    engineer = _fresh_engineer(スキル=["Java", "Python", "AWS"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
    assert any("語彙外スキル" in r and "MATCH判定" in r for r in reasons)


def test_review_when_unknown_ratio_exceeds_30_percent():
    """語彙外スキル(証拠なし)が30%超の場合はREVIEW"""
    case = {
        "required_skills": ["Java", "OpenShift", "Maximo"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    # OpenShift/Maximoは辞書外・証拠なし (2/3≈67%>30%)
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "REVIEW"
    assert any("語彙外必須スキル要確認" in r for r in reasons)


def test_match_unknown_with_evidence_does_not_count_toward_ratio():
    """unknown_with_evidenceはratioに含まれないのでMATCH"""
    case = {
        "required_skills": ["Java", "OpenShift", "Maximo"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    # OpenShift/MaximoはエンジニアのDBに生スキルとして存在 → evidence → ratio=0/3=0%
    engineer = _fresh_engineer(スキル=["Java", "OpenShift", "Maximo"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"


# --- 新規スキルのnormalize_hard()テスト（代表20語） ---

def test_normalize_excel():
    assert _normalizer().normalize_hard("Microsoft Excel") == "Excel"

def test_normalize_excel_lowercase():
    assert _normalizer().normalize_hard("ms excel") == "Excel"

def test_normalize_git():
    assert _normalizer().normalize_hard("git") == "Git"

def test_normalize_github():
    assert _normalizer().normalize_hard("github") == "GitHub"

def test_normalize_next_js():
    assert _normalizer().normalize_hard("Nextjs") == "Next.js"

def test_normalize_react_native():
    assert _normalizer().normalize_hard("react-native") == "React Native"

def test_normalize_laravel():
    assert _normalizer().normalize_hard("laravel") == "Laravel"

def test_normalize_cpp():
    assert _normalizer().normalize_hard("CPP") == "C++"

def test_normalize_vmware():
    assert _normalizer().normalize_hard("VMWare") == "VMware"

def test_normalize_oci():
    assert _normalizer().normalize_hard("Oracle Cloud Infrastructure") == "OCI"

def test_normalize_dwh():
    assert _normalizer().normalize_hard("Data Warehouse") == "DWH"

def test_normalize_etl():
    assert _normalizer().normalize_hard("Extract Transform Load") == "ETL"

def test_normalize_rdbms():
    assert _normalizer().normalize_hard("Relational Database") == "RDBMS"

def test_normalize_power_platform():
    assert _normalizer().normalize_hard("Microsoft Power Platform") == "Power Platform"

def test_normalize_snowflake():
    assert _normalizer().normalize_hard("snowflake") == "Snowflake"

def test_normalize_databricks():
    assert _normalizer().normalize_hard("databricks") == "Databricks"

def test_normalize_zabbix():
    assert _normalizer().normalize_hard("zabbix") == "Zabbix"

def test_normalize_flutter():
    assert _normalizer().normalize_hard("flutter") == "Flutter"

def test_normalize_powershell():
    assert _normalizer().normalize_hard("pwsh") == "PowerShell"

def test_normalize_ruby_on_rails():
    assert _normalizer().normalize_hard("Rails") == "Ruby on Rails"


# --- process_skill除外テスト ---

def test_is_process_skill_basic():
    assert _is_process_skill("要件定義") is True

def test_is_process_skill_sekkei():
    assert _is_process_skill("基本設計") is True

def test_is_process_skill_test():
    assert _is_process_skill("テスト") is True

def test_is_process_skill_false_for_tech():
    assert _is_process_skill("Python") is False

def test_is_process_skill_false_for_soft():
    assert _is_process_skill("コミュニケーション") is False


def test_match_when_required_skills_are_process_skills_only():
    """process_skillのみの案件はMATCH（能力記述と同等扱い）"""
    case = {
        "required_skills": ["要件定義", "基本設計", "詳細設計"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["Java"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"


def test_match_when_required_skill_mix_tech_and_process():
    """tech_skill(Python)とprocess_skill(テスト)が混在→process_skillを除外してtechのみ評価"""
    case = {
        "required_skills": ["Python", "テスト実施", "構築"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["Python"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"


def test_ng_when_tech_skill_missing_even_with_process_skills():
    """process_skillのみ持ちでtech_skill必須 → NG"""
    case = {
        "required_skills": ["Java", "要件定義", "基本設計"],
        "price_max": 80,
        "extraction_confidence": 1.0,
    }
    engineer = _fresh_engineer(スキル=["Python"])  # Javaなし

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "NG"
    assert "必須スキル不足" in reasons[0]


def test_match_new_skill_databricks_in_dict():
    """Databricksが辞書に追加され、エンジニアが持てばMATCH"""
    case = {"required_skills": ["Databricks"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Databricks"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"


def test_match_new_skill_snowflake_in_dict():
    """Snowflakeが辞書に追加済み→エンジニア保有でMATCH"""
    case = {"required_skills": ["Snowflake"], "price_max": 80, "extraction_confidence": 1.0}
    engineer = _fresh_engineer(スキル=["Snowflake"])

    verdict, reasons = judge(case, engineer, _normalizer())

    assert verdict == "MATCH"
