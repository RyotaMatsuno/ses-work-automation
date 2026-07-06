"""Tests for engineer_text_parser."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pytest
from engineer_extractor.engineer_text_parser import (
    ParsedEngineerText,
    parse_engineer_text,
    PATTERN_AUTO_IMPORT,
    PATTERN_EMAIL_REGISTER,
    PATTERN_LINE_REGISTER,
    PATTERN_UNKNOWN,
)
from engineer_extractor.tests.fixtures.sample_texts import (
    SAMPLE_AUTO_IMPORT,
    SAMPLE_EMAIL_REGISTER,
    SAMPLE_LINE_REGISTER,
    SAMPLE_LINE_REGISTER_AUTO,
    SAMPLE_UNKNOWN,
    SAMPLE_EMPTY,
    SAMPLE_WHITESPACE,
)


class TestPatternDetection:
    def test_auto_import_pattern(self):
        result = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        assert result.pattern_type == PATTERN_AUTO_IMPORT

    def test_email_register_pattern(self):
        result = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        assert result.pattern_type == PATTERN_EMAIL_REGISTER

    def test_line_register_pattern(self):
        result = parse_engineer_text(SAMPLE_LINE_REGISTER)
        assert result.pattern_type == PATTERN_LINE_REGISTER

    def test_line_register_auto_pattern(self):
        result = parse_engineer_text(SAMPLE_LINE_REGISTER_AUTO)
        assert result.pattern_type == PATTERN_LINE_REGISTER

    def test_unknown_pattern(self):
        result = parse_engineer_text(SAMPLE_UNKNOWN)
        assert result.pattern_type == PATTERN_UNKNOWN


class TestSubjectExtraction:
    def test_auto_import_subject(self):
        result = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        assert result.subject is not None
        assert "SasaTech" in result.subject
        assert "65万" in result.subject

    def test_email_register_subject(self):
        result = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        assert result.subject is not None
        assert "蕨駅" in result.subject
        assert "iOS開発11年" in result.subject

    def test_line_register_no_subject(self):
        result = parse_engineer_text(SAMPLE_LINE_REGISTER)
        assert result.subject is None


class TestSenderExtraction:
    def test_auto_import_sender(self):
        result = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        assert result.sender is not None
        assert "SasaTech" in result.sender

    def test_email_register_sender(self):
        result = parse_engineer_text(SAMPLE_EMAIL_REGISTER)
        assert result.sender is not None
        assert "conviction-inc.com" in result.sender

    def test_received_date(self):
        result = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        assert result.received_date is not None
        assert "2026" in result.received_date


class TestLabeledFieldsExtraction:
    def test_line_register_skills(self):
        result = parse_engineer_text(SAMPLE_LINE_REGISTER)
        assert "スキル" in result.labeled_fields
        assert "PHP" in result.labeled_fields["スキル"]

    def test_line_register_rate(self):
        result = parse_engineer_text(SAMPLE_LINE_REGISTER)
        assert "単価" in result.labeled_fields
        assert "40万円" in result.labeled_fields["単価"]

    def test_line_register_station(self):
        result = parse_engineer_text(SAMPLE_LINE_REGISTER)
        assert "最寄" in result.labeled_fields
        assert "船橋競馬場駅" in result.labeled_fields["最寄"]

    def test_line_register_name(self):
        result = parse_engineer_text(SAMPLE_LINE_REGISTER)
        assert "名前" in result.labeled_fields
        assert "Y.S" in result.labeled_fields["名前"]


class TestEdgeCases:
    def test_empty_text(self):
        result = parse_engineer_text(SAMPLE_EMPTY)
        assert result.pattern_type == PATTERN_UNKNOWN
        assert result.subject is None
        assert result.body == ""

    def test_whitespace_only(self):
        result = parse_engineer_text(SAMPLE_WHITESPACE)
        assert result.pattern_type == PATTERN_UNKNOWN
        assert result.subject is None

    def test_full_text_preserved(self):
        result = parse_engineer_text(SAMPLE_AUTO_IMPORT)
        assert result.full_text == SAMPLE_AUTO_IMPORT

    def test_no_labeled_fields_in_plain_text(self):
        result = parse_engineer_text("普通のテキストです。スキルなし。")
        assert result.labeled_fields == {}
