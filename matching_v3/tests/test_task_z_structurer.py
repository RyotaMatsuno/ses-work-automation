from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import structurer


class DummyCostGuard:
    def can_call(self, est_input_tokens, est_output_tokens):
        return True

    def get_model(self):
        return "model"

    def record_cost(self, input_tokens, output_tokens, model):
        pass


class DummyConfig:
    anthropic_api_key = "secret"


def _response(text: str):
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )


def test_notion_direct_skips_llm():
    case = {
        "id": "case-1",
        "案件名": "Java案件",
        "必要スキル": ["Java", "Spring"],
        "単価（万円）": 70.0,
    }
    guard = DummyCostGuard()

    with patch("structurer._call_anthropic") as mock_call:
        result = structurer.structure_case(case, "本文", guard, DummyConfig())

    mock_call.assert_not_called()
    assert result["required_skills"] == ["Java", "Spring"]
    assert result["price_min"] == 70.0
    assert result["structure_source"] == "notion_direct"


def test_rule_fallback_extracts_react_java_subject():
    subject = "React+Java 基本設計～ 基幹システム刷新"
    body = "単価：70万\n必須：React, Java"

    result = structurer.rule_based_fallback(subject, body)

    assert "react" in result["required_skills"]
    assert "java" in result["required_skills"]
    assert result["price_min"] == 70.0
    assert structurer.is_recoverable(result)


def test_json_parse_failure_uses_rule_fallback():
    subject = "医療系AI SaaSにおけるモバイルアプリ開発（Swift/Kotlin）"
    body = "単価60万\n必須：Swift, Kotlin"

    result = structurer._parse_json_or_fallback("not json", subject, body)

    assert "swift" in result["required_skills"]
    assert result["price_min"] == 60.0
    assert result["structure_source"] == "rule_fallback"


def test_llm_failure_merges_rule_prefill():
    case = {"案件名": "WEBディレクター案件"}
    body = "単価：55万\nPM経験必須"
    guard = DummyCostGuard()

    with patch("structurer._call_anthropic", return_value=_response("not json")):
        result = structurer.structure_case(case, body, guard, DummyConfig())

    assert result["price_min"] == 55.0
    assert structurer.is_recoverable(result)
