# -*- coding: utf-8 -*-
"""Task Q: price_extractor / skill_extractor tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from mail_pipeline.price_extractor import extract_price, resolve_final_price
from mail_pipeline.skill_extractor import extract_skills, merge_extracted_skills, normalize_to_valid_skills

VALID = ["Java", "Spring", "Oracle", "MySQL", "React", "Vue.js", "TypeScript", "Python", "AWS"]


class TestPriceExtractor:
    def test_tilde_65_man(self):
        r = extract_price("PMO案件/〜65万/損保", "")
        assert r["value"] == 65
        assert r["unit"] == "monthly"
        assert r["confidence"] == "high"

    def test_range_80_100(self):
        r = extract_price("", "予算80〜100万円")
        assert r["value"] == 80
        assert r["unit"] == "monthly"
        assert r["confidence"] == "high"

    def test_annual_salary(self):
        r = extract_price("", "想定年収625万")
        assert r["value"] == 625
        assert r["unit"] == "annual"
        assert r["confidence"] == "high"
        assert r["normalized_monthly"] == pytest.approx(52.1, abs=0.1)

    def test_daily_rate(self):
        r = extract_price("", "単価1.5万/日")
        assert r["value"] == 1.5
        assert r["unit"] == "daily"
        assert r["confidence"] == "high"
        assert r["normalized_monthly"] == 30

    def test_max_90(self):
        r = extract_price("MAX90万", "")
        assert r["value"] == 90
        assert r["unit"] == "monthly"
        assert r["confidence"] == "high"

    def test_suspicious_875(self):
        r = extract_price("", "875万")
        assert r["value"] == 875
        assert r["confidence"] == "suspicious"

    def test_resolve_prefers_high_monthly_rule(self):
        assert resolve_final_price(None, "〜65万", "") == 65

    def test_resolve_ai_in_range(self):
        assert resolve_final_price(80, "", "no price here") == 80

    def test_resolve_rejects_suspicious(self):
        assert resolve_final_price(None, "", "875万") is None


class TestSkillExtractor:
    def test_header_necessary_skills(self):
        r = extract_skills("", "【必要スキル】Java, Spring Boot, Oracle\n")
        assert "java" in r["required"]
        assert "spring boot" in r["required"]
        assert "oracle" in r["required"]

    def test_header_required_block(self):
        r = extract_skills("", "■必須：Java（3年以上）、SQL\n")
        assert "java" in r["required"]
        assert "sql" in r["required"]

    def test_dictionary_scan(self):
        r = extract_skills("", "React/Vue/TypeScript フロント開発")
        assert "react" in r["required"]
        assert "vue" in r["required"]
        assert "typescript" in r["required"]
        assert r["source"] == "dictionary"

    def test_pmo_from_subject(self):
        r = extract_skills("PMO案件/〜65万", "")
        assert "pmo" in r["required"]

    def test_merge_with_valid_skills(self):
        req, opt = merge_extracted_skills([], [], "PMO案件", "【必要スキル】Java\n", VALID)
        assert "Java" in req

    def test_normalize_aliases(self):
        out = normalize_to_valid_skills(["java", "spring boot", "oracle"], VALID)
        assert "Java" in out
        assert "Spring" in out
        assert "Oracle" in out
