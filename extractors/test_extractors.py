# -*- coding: utf-8 -*-
"""Unit tests for R5 extractors."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SES_WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SES_WORK))

from extractors.location_extractor import extract_location
from extractors.rate_extractor import extract_rate
from extractors.remote_extractor import extract_remote


class TestRateExtractor:
    def test_fixed_range(self):
        result = extract_rate("単価: 55万〜65万")
        assert result.rate_type == "fixed_range"
        assert result.rate_min_man == 55
        assert result.rate_max_man == 65

    def test_skill_dependent_with_cap(self):
        result = extract_rate("スキル見合い MAX75万")
        assert result.rate_type == "skill_dependent_with_cap"
        assert result.rate_max_man == 75

    def test_fixed_upper_only(self):
        result = extract_rate("上限70万まで")
        assert result.rate_type == "fixed_upper_only"
        assert result.rate_max_man == 70

    def test_context_price(self):
        result = extract_rate("予算: 65万")
        assert result.rate_max_man == 65
        assert result.confidence == 0.75

    def test_skill_dependent_no_number(self):
        result = extract_rate("単価はスキル見合いです")
        assert result.rate_type == "skill_dependent_no_number"

    def test_not_present(self):
        result = extract_rate("Java開発の案件です")
        assert result.rate_type == "not_present"

    def test_needs_llm_fallback(self):
        result = extract_rate("予算は交渉（数値記載なし）")
        assert result.needs_llm_fallback is True

    def test_bugfix_skill_before_miawase(self):
        result = extract_rate("70万（スキル見合い）")
        assert result.rate_type == "skill_dependent_with_cap"
        assert result.rate_max_man == 70

    def test_bugfix_tanka_55_man(self):
        result = extract_rate("単価：55万")
        assert result.rate_max_man == 55
        assert result.rate_max_man != 550000

    def test_bugfix_approx_50_man(self):
        result = extract_rate("50万円前後")
        assert result.rate_type == "fixed_upper_only"
        assert result.rate_max_man == 50

    def test_validate_rate_rejects_yen_scale(self):
        import pytest
        from extractors.rate_extractor import validate_rate_man
        with pytest.raises(ValueError):
            validate_rate_man(550000)

    def test_reject_over_200(self):
        result = extract_rate("単価: 300万")
        assert result.rate_max_man is None
        assert result.needs_review is True

    def test_low_confidence_under_10(self):
        result = extract_rate("単価: 5万")
        assert result.rate_type == "unknown" or result.needs_review is True

    def test_swap_min_max(self):
        result = extract_rate("70万〜60万")
        assert result.rate_min_man == 60
        assert result.rate_max_man == 70

    def test_empty_text(self):
        result = extract_rate("")
        assert result.rate_type == "not_present"


class TestRemoteExtractor:
    def test_full_remote(self):
        result = extract_remote("フルリモート案件")
        assert result.remote_type == "full_remote"

    def test_hybrid_with_days(self):
        result = extract_remote("週2出社、基本リモート")
        assert result.remote_type == "hybrid"
        assert result.onsite_days_per_week == 2

    def test_onsite(self):
        result = extract_remote("常駐案件です")
        assert result.remote_type == "onsite"

    def test_remote_possible(self):
        result = extract_remote("テレワーク可能")
        assert result.remote_type == "remote_possible"

    def test_unknown(self):
        result = extract_remote("Java案件")
        assert result.remote_type == "unknown"

    def test_contradiction(self):
        result = extract_remote("フルリモートだが常駐必須")
        assert result.needs_llm_fallback is True

    def test_initial_onsite(self):
        result = extract_remote("フルリモート。初日出社後は在宅")
        assert result.remote_type == "full_remote"
        assert result.initial_onsite_required is True

    def test_full_remote_initial_onsite_day1(self):
        result = extract_remote("フルリモート案件。初日出社有")
        assert result.remote_type == "full_remote"
        assert result.initial_onsite_required is True

    def test_empty_text(self):
        result = extract_remote("")
        assert result.remote_type == "unknown"


class TestLocationExtractor:
    def test_standard(self):
        result = extract_location("勤務地: 東京都港区")
        assert result.location == "東京都港区"
        assert result.area == "東京都"

    def test_bracket(self):
        result = extract_location("【勤務地】新宿")
        assert result.location == "新宿"

    def test_station(self):
        result = extract_location("最寄り駅: 品川駅")
        assert result.station == "品川駅"

    def test_remote_only_none_location(self):
        result = extract_location("勤務地: リモート")
        assert result.location is None

    def test_none(self):
        result = extract_location("Javaの案件です")
        assert result.location is None

    def test_empty_text(self):
        result = extract_location("")
        assert result.location is None

    def test_large_text(self):
        body = "x" * 10000 + "\n勤務地: 渋谷区\n"
        result = extract_location(body)
        assert result.location == "渋谷区"


class TestZeroManSamples:
    @pytest.mark.parametrize(
        "text,expected_type",
        [
            ("スキル見合い MAX70万", "skill_dependent_with_cap"),
            ("60万〜70万", "fixed_range"),
            ("フルリモート", "full_remote"),
        ],
    )
    def test_known_zero_man_patterns(self, text, expected_type):
        if expected_type.startswith("skill") or expected_type.startswith("fixed"):
            assert extract_rate(text).rate_type == expected_type
        else:
            assert extract_remote(text).remote_type == expected_type
