"""Tests for all field extractors."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pytest
from engineer_extractor.engineer_text_parser import parse_engineer_text
from engineer_extractor.field_extractors.skills_extractor import extract_skills
from engineer_extractor.field_extractors.rate_extractor_eng import extract_rate
from engineer_extractor.field_extractors.station_extractor import extract_station
from engineer_extractor.field_extractors.experience_extractor import extract_experience
from engineer_extractor.field_extractors.availability_extractor import extract_availability
from engineer_extractor.field_extractors.demographics_extractor import extract_demographics
from engineer_extractor.tests.fixtures.sample_texts import (
    SAMPLE_AUTO_IMPORT,
    SAMPLE_EMAIL_REGISTER,
    SAMPLE_LINE_REGISTER,
    SAMPLE_UNKNOWN,
    SAMPLE_EMPTY,
)


class TestSkillsExtractor:
    def test_line_register_labeled_skills(self):
        parsed = parse_engineer_text(SAMPLE_LINE_REGISTER)
        result = extract_skills(parsed)
        assert result.confidence >= 0.9
        assert result.source == "labeled"
        assert "PHP" in result.skills

    def test_auto_import_subject_skills(self):
        parsed = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        result = extract_skills(parsed)
        assert len(result.skills) > 0
        assert any(s in result.skills for s in ["Linux", "JP1", "RHEL", "CLUSTERPRO"])

    def test_email_register_subject_skills(self):
        parsed = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        result = extract_skills(parsed)
        assert len(result.skills) > 0
        assert any(s in result.skills for s in ["Swift", "Kotlin", "Java"])

    def test_empty_text_no_skills(self):
        parsed = parse_engineer_text(SAMPLE_EMPTY)
        result = extract_skills(parsed)
        assert result.skills == []
        assert result.confidence == 0.0

    def test_dictionary_matching(self):
        text = "Python, Django, PostgreSQL, Docker, GitHubが使えます。"
        parsed = parse_engineer_text(text)
        result = extract_skills(parsed)
        assert "Python" in result.skills
        assert "Docker" in result.skills


class TestRateExtractor:
    def test_line_register_labeled_rate(self):
        parsed = parse_engineer_text(SAMPLE_LINE_REGISTER)
        result = extract_rate(parsed)
        assert result.rate == 40
        assert result.source == "labeled"
        assert result.confidence >= 0.8

    def test_auto_import_subject_bracket_rate(self):
        parsed = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        result = extract_rate(parsed)
        assert result.rate == 65
        assert result.negotiable is True

    def test_email_register_body_rate(self):
        parsed = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        result = extract_rate(parsed)
        assert result.rate == 75

    def test_range_rate(self):
        text = "単価：60〜70万で考えています。"
        parsed = parse_engineer_text(text)
        result = extract_rate(parsed)
        assert result.rate_min == 60
        assert result.rate_max == 70
        assert result.rate == 70  # max used per SES convention

    def test_empty_returns_zero_confidence(self):
        parsed = parse_engineer_text(SAMPLE_EMPTY)
        result = extract_rate(parsed)
        assert result.confidence == 0.0
        assert result.rate is None

    def test_skill_dependent(self):
        text = "単価はスキル見合いで応相談"
        parsed = parse_engineer_text(text)
        result = extract_rate(parsed)
        assert result.skill_dependent is True or result.negotiable is True


class TestStationExtractor:
    def test_line_register_labeled_station(self):
        parsed = parse_engineer_text(SAMPLE_LINE_REGISTER)
        result = extract_station(parsed)
        assert result.station == "船橋競馬場駅"
        assert result.source == "labeled"
        assert result.confidence >= 0.9

    def test_auto_import_body_station(self):
        parsed = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        result = extract_station(parsed)
        assert result.station is not None
        assert "横浜" in result.station

    def test_email_register_body_station(self):
        parsed = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        result = extract_station(parsed)
        assert result.station is not None
        assert "大宮" in result.station

    def test_subject_pipe_station(self):
        text = "【メールから自動登録】\n送信者: test@example.com\n件名: D.E｜蕨駅｜iOS開発11年\n本文"
        parsed = parse_engineer_text(text)
        result = extract_station(parsed)
        assert result.station is not None
        assert "蕨駅" in result.station

    def test_empty_returns_none(self):
        parsed = parse_engineer_text(SAMPLE_EMPTY)
        result = extract_station(parsed)
        assert result.station is None

    def test_station_without_suffix_and_no_false_positive(self):
        text = (
            "【メールから自動登録】\n"
            "送信者: test@example.com\n"
            "件名: COBOL/7月～/60万\n"
            "57歳、最寄り駅：西巣鴨、プロパー社員"
        )
        parsed = parse_engineer_text(text)
        result = extract_station(parsed)
        assert result.station == "西巣鴨駅"
        assert result.station != "り駅"


class TestExperienceExtractor:
    def test_subject_experience_years(self):
        parsed = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        result = extract_experience(parsed)
        assert result.years == 11
        assert result.confidence >= 0.8

    def test_body_experience_years(self):
        parsed = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        result = extract_experience(parsed)
        assert result.years == 10

    def test_unknown_pattern_experience(self):
        parsed = parse_engineer_text(SAMPLE_UNKNOWN)
        result = extract_experience(parsed)
        assert result.years == 3.5

    def test_empty_returns_none(self):
        parsed = parse_engineer_text(SAMPLE_EMPTY)
        result = extract_experience(parsed)
        assert result.years is None


class TestAvailabilityExtractor:
    def test_line_register_labeled_availability(self):
        parsed = parse_engineer_text(SAMPLE_LINE_REGISTER)
        result = extract_availability(parsed)
        assert result.start_date is not None
        assert "-07-01" in result.start_date
        assert result.inferred_year is True

    def test_immediate(self):
        parsed = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        result = extract_availability(parsed)
        assert result.is_immediate is True

    def test_iso_date(self):
        parsed = parse_engineer_text(SAMPLE_UNKNOWN)
        result = extract_availability(parsed)
        assert result.start_date == "2026-08-01"
        assert result.inferred_year is False

    def test_auto_import_date(self):
        parsed = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        result = extract_availability(parsed)
        assert result.start_date is not None
        assert "2026-07" in result.start_date

    def test_empty_returns_none(self):
        parsed = parse_engineer_text(SAMPLE_EMPTY)
        result = extract_availability(parsed)
        assert result.start_date is None


class TestDemographicsExtractor:
    def test_line_register_name_field(self):
        parsed = parse_engineer_text(SAMPLE_LINE_REGISTER)
        result = extract_demographics(parsed)
        assert result.age == 33
        assert result.gender == "男性"
        assert result.confidence >= 0.85

    def test_auto_import_body_age_gender(self):
        parsed = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        result = extract_demographics(parsed)
        assert result.age == 40
        assert result.gender == "男性"

    def test_email_register_gender(self):
        parsed = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        result = extract_demographics(parsed)
        assert result.gender == "女性"
        assert result.age == 40

    def test_empty_returns_none(self):
        parsed = parse_engineer_text(SAMPLE_EMPTY)
        result = extract_demographics(parsed)
        assert result.age is None
        assert result.gender is None
