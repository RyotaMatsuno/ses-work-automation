"""Tests for merge_policy."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pytest
from engineer_extractor.merge_policy import decide_merge, MergeDecision


class TestEmptyDetection:
    def test_none_is_empty(self):
        decisions = decide_merge(
            {"最寄り駅": None},
            {"最寄り駅": "横浜駅"},
            {"最寄り駅": 0.9},
            {"最寄り駅": "labeled"},
        )
        assert decisions[0].action == "update"

    def test_empty_string_is_empty(self):
        decisions = decide_merge(
            {"最寄り駅": ""},
            {"最寄り駅": "横浜駅"},
            {"最寄り駅": 0.9},
        )
        assert decisions[0].action == "update"

    def test_whitespace_is_empty(self):
        decisions = decide_merge(
            {"最寄り駅": "   "},
            {"最寄り駅": "横浜駅"},
            {"最寄り駅": 0.9},
        )
        assert decisions[0].action == "update"

    def test_empty_list_is_empty(self):
        decisions = decide_merge(
            {"スキル": []},
            {"スキル": ["Python", "Java"]},
            {"スキル": 0.92},
        )
        assert decisions[0].action == "update"

    def test_rate_zero_is_empty(self):
        decisions = decide_merge(
            {"単価（万円）": 0},
            {"単価（万円）": 65},
            {"単価（万円）": 0.88},
        )
        assert decisions[0].action == "update"

    def test_rate_none_is_empty(self):
        decisions = decide_merge(
            {"単価（万円）": None},
            {"単価（万円）": 65},
            {"単価（万円）": 0.88},
        )
        assert decisions[0].action == "update"


class TestExistingValueProtection:
    def test_existing_value_is_skipped(self):
        decisions = decide_merge(
            {"最寄り駅": "新宿駅"},
            {"最寄り駅": "渋谷駅"},
            {"最寄り駅": 0.90},
        )
        assert decisions[0].action == "skip_existing"

    def test_existing_skills_not_overwritten(self):
        decisions = decide_merge(
            {"スキル": ["Java", "Spring"]},
            {"スキル": ["Python", "Django"]},
            {"スキル": 0.95},
        )
        assert decisions[0].action == "skip_existing"

    def test_existing_rate_not_overwritten(self):
        decisions = decide_merge(
            {"単価（万円）": 70},
            {"単価（万円）": 65},
            {"単価（万円）": 0.88},
        )
        assert decisions[0].action == "skip_existing"


class TestLowConfidenceSkip:
    def test_low_confidence_skipped(self):
        decisions = decide_merge(
            {"経験年数": None},
            {"経験年数": 5},
            {"経験年数": 0.4},
        )
        assert decisions[0].action == "skip_no_value"

    def test_confidence_exactly_half_skipped_for_other_fields(self):
        decisions = decide_merge(
            {"スキル": []},
            {"スキル": ["Python"]},
            {"スキル": 0.5},
        )
        assert decisions[0].action == "update"

    def test_experience_below_field_minimum_skipped(self):
        decisions = decide_merge(
            {"経験年数": None},
            {"経験年数": 8},
            {"経験年数": 0.65},
        )
        assert decisions[0].action == "skip_no_value"

    def test_experience_at_field_minimum_updates(self):
        decisions = decide_merge(
            {"経験年数": None},
            {"経験年数": 8},
            {"経験年数": 0.70},
        )
        assert decisions[0].action == "update"


class TestNoExtractedValue:
    def test_none_extracted_skipped(self):
        decisions = decide_merge(
            {"経験年数": None},
            {"経験年数": None},
            {"経験年数": 0.9},
        )
        assert decisions[0].action == "skip_no_value"

    def test_empty_list_extracted_skipped(self):
        decisions = decide_merge(
            {"スキル": []},
            {"スキル": []},
            {"スキル": 0.95},
        )
        assert decisions[0].action == "skip_no_value"


class TestMultipleFields:
    def test_multiple_fields_mixed(self):
        existing = {
            "スキル": [],
            "単価（万円）": 50,
            "最寄り駅": None,
            "経験年数": 5,
        }
        extracted = {
            "スキル": ["Python", "Docker"],
            "単価（万円）": 65,
            "最寄り駅": "渋谷駅",
            "経験年数": 8,
        }
        confidences = {k: 0.90 for k in extracted}
        decisions = decide_merge(existing, extracted, confidences)

        by_field = {d.field: d for d in decisions}
        assert by_field["スキル"].action == "update"        # empty list -> update
        assert by_field["単価（万円）"].action == "skip_existing"  # 50 exists
        assert by_field["最寄り駅"].action == "update"      # None -> update
        assert by_field["経験年数"].action == "skip_existing"  # 5 exists
