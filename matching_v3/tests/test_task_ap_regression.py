from __future__ import annotations

from datetime import datetime, timezone

from matcher import SkillNormalizer
from notifier import build_proposal_summary


def _normalizer() -> SkillNormalizer:
    return SkillNormalizer("skill_aliases.json")


def _fresh_engineer(**overrides):
    base = {
        "名前": "田中 太郎",
        "単価（万円）": 70,
        "経験年数": 8,
        "スキル": ["Java", "Spring", "MySQL", "AWS"],
        "稼働状況": "即日可",
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
        "備考（LINEメモ）": "",
    }
    base.update(overrides)
    return base


def _case(**overrides):
    base = {
        "案件名": "Java/Spring案件",
        "required_skills": ["Java", "Spring", "MySQL"],
        "optional_skills": ["AWS"],
        "price_min": 60.0,
        "price_max": 75.0,
        "start_date": "2026-07-01",
    }
    base.update(overrides)
    return base


def test_build_proposal_summary_match_includes_skill_buckets_and_gross():
    summary = build_proposal_summary(_case(), _fresh_engineer(), "MATCH", [], normalizer=_normalizer())

    assert "完全一致" in summary["internal_text"]
    assert "Java" in summary["skill_matches"]["exact"]
    assert summary["price_info"]["gross_profit"] == 5.0
    assert "必須・尚可ともにマッチ度高い人員" in summary["appeal"]
    assert "ご検討いただけますと幸いです" in summary["client_text"]


def test_build_proposal_summary_alias_match_listed():
    engineer = _fresh_engineer(スキル=["tf", "ci", "llm", "Java", "Spring", "MySQL"])
    case = _case(required_skills=["Terraform", "CI/CD", "生成AI", "Java", "Spring", "MySQL"], optional_skills=[])
    summary = build_proposal_summary(case, engineer, "MATCH", [], normalizer=_normalizer())

    assert "Terraform" in summary["skill_matches"]["alias"]
    assert "alias一致" in summary["internal_text"]


def test_build_proposal_summary_required_only_appeal():
    case = _case(optional_skills=[])
    summary = build_proposal_summary(case, _fresh_engineer(スキル=["Java", "Spring", "MySQL"]), "MATCH", [], normalizer=_normalizer())

    assert summary["appeal"] == "必須スキル全て満たし即稼働可能"


def test_build_proposal_summary_review_includes_concerns_and_reasons():
    engineer = _fresh_engineer(
        _last_edited_time="2026-01-01T00:00:00+00:00",
    )
    engineer["備考（LINEメモ）"] = "面談調整中"
    reasons = ["エンジニア情報古い（120日前更新）", "曖昧スキルあり: ['クラウド経験']"]
    summary = build_proposal_summary(_case(), engineer, "REVIEW", reasons, normalizer=_normalizer())

    assert "【REVIEW】" in summary["internal_text"]
    assert any("鮮度警告" in item for item in summary["concerns"])
    assert any("並行状況" in item for item in summary["concerns"])
    assert "判定根拠:" in summary["internal_text"]


def test_build_proposal_summary_start_date_misaligned():
    engineer = _fresh_engineer(稼働開始="2026-08-01", 稼働状況="")
    summary = build_proposal_summary(_case(start_date="2026-07-01"), engineer, "MATCH", [], normalizer=_normalizer())

    assert summary["start_info"]["aligned"] is False
    assert any("稼働開始" in item for item in summary["concerns"])
