from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

import structurer


class DummyCostGuard:
    def __init__(self) -> None:
        self.recorded = False

    def can_call(self, est_input_tokens, est_output_tokens, target_id=""):
        return True

    def get_model(self):
        return "model"

    def record_cost(self, input_tokens, output_tokens, model):
        self.recorded = True

    def abort_pending(self, error_kind: str = "transient"):
        pass


class DummyConfig:
    anthropic_api_key = "secret"


def _response(text: str):
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )


def test_fixture_input_returns_expected_json():
    fixture = json.loads((structurer.BASE_DIR / "tests" / "fixtures.json").read_text(encoding="utf-8"))
    expected = fixture["case_examples"][0]["expected"]
    guard = DummyCostGuard()

    with patch("structurer._call_anthropic", return_value=_response(json.dumps(expected, ensure_ascii=False))):
        result = structurer.structure(fixture["case_examples"][0]["body"], guard, DummyConfig())

    assert result["required_skills"] == expected["required_skills"]
    assert result["price_min"] == expected["price_min"]
    assert result["price_max"] == expected["price_max"]
    assert result["extraction_confidence"] >= 0.75
    assert guard.recorded is True


def test_long_body_is_truncated_to_head_and_tail():
    body = "A" * 2500 + "B" * 1500
    truncated = structurer._truncate_body(body)

    assert len(truncated) == 3000
    assert truncated.startswith("A" * 2000)
    assert truncated.endswith("B" * 1000)


def test_json_parse_failure_returns_rule_fallback():
    subject = "Java案件"
    body = "単価70万 必須：Java"
    result = structurer._parse_json_or_fallback("not json", subject, body)

    assert result["extraction_confidence"] >= 0.4
    assert any(s.lower() == "java" for s in result["required_skills"])
