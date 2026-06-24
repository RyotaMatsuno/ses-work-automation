"""Task M: Gemini→Claude Sonnet差替えのテスト。"""

from __future__ import annotations

import io
import logging
import sys
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

GATE_CHECKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE_CHECKER_DIR))
sys.path.insert(0, str(GATE_CHECKER_DIR.parent))

import agreement_checker
import gate_check


def test_daily_call_limit_is_30() -> None:
    assert gate_check.DAILY_CALL_LIMIT == 30


def test_system_prompts_include_costguard_note() -> None:
    note = gate_check.COSTGUARD_NOTE
    for prompt in (
        gate_check.REQUIREMENTS_SYSTEM,
        gate_check.DESIGN_SYSTEM,
        gate_check.IMPLEMENTATION_SYSTEM,
        gate_check.TEST_SYSTEM,
    ):
        assert "CostGuardはLLM API呼び出し" in prompt
        assert "Notion API" in prompt
        assert "承認済みの仕様変更" in prompt
        assert note.strip() in prompt


def test_extract_sonnet_text_raises_on_empty_content() -> None:
    with pytest.raises(ValueError, match="空レスポンス"):
        agreement_checker._extract_sonnet_text({"content": []})


def test_extract_sonnet_text_parses_valid_response() -> None:
    data = {
        "content": [{"type": "text", "text": "問題なし\n【判定: GO】"}],
        "stop_reason": "end_turn",
    }
    text = agreement_checker._extract_sonnet_text(data)
    assert "【判定: GO】" in text


def test_sonnet_http_error_logs_status(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR, logger="agreement_checker")

    body = b'{"error":{"message":"forbidden"}}'
    http_error = urllib.error.HTTPError(
        url="http://test",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=io.BytesIO(body),
    )

    with mock.patch("urllib.request.urlopen", side_effect=http_error):
        with mock.patch.object(agreement_checker, "_CG_OK", False):
            result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "ERROR"
    assert "403" in result.error
    assert any("403" in rec.message for rec in caplog.records)


def test_call_sonnet_records_cost_via_ledger() -> None:
    response_data = {
        "content": [{"type": "text", "text": "問題なし\n【判定: GO】"}],
        "usage": {"input_tokens": 120, "output_tokens": 80},
        "stop_reason": "end_turn",
    }

    class FakeResp:
        def read(self) -> bytes:
            import json

            return json.dumps(response_data).encode("utf-8")

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
        with mock.patch.object(agreement_checker, "_CG_OK", False):
            with mock.patch.object(agreement_checker, "_ledger_record") as record_mock:
                result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "OK"
    record_mock.assert_called_once()
    args = record_mock.call_args[0]
    assert args[0] == 120
    assert args[1] == 80
    assert args[2] == agreement_checker.SONNET_MODEL
    assert args[3] == "gate_checker"
    assert record_mock.call_args[1]["phase"] == "review_sonnet"


def test_call_sonnet_uses_costguard_allowed_finalize() -> None:
    fake_decision = mock.Mock()
    fake_decision.exit_code = 0
    fake_decision.allowed = True

    response_data = {
        "content": [{"type": "text", "text": "問題なし\n【判定: GO】"}],
        "usage": {"input_tokens": 50, "output_tokens": 25},
        "stop_reason": "end_turn",
    }

    class FakeResp:
        def read(self) -> bytes:
            import json

            return json.dumps(response_data).encode("utf-8")

        def __enter__(self) -> FakeResp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    with mock.patch("urllib.request.urlopen", return_value=FakeResp()):
        with mock.patch.object(agreement_checker, "_CG_OK", True):
            with mock.patch.object(agreement_checker, "_cg_allowed", return_value=fake_decision) as allowed_mock:
                with mock.patch.object(agreement_checker, "_cg_finalize") as finalize_mock:
                    result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "OK"
    allowed_mock.assert_called_once()
    kwargs = allowed_mock.call_args[1]
    assert kwargs["phase"] == "review_sonnet"
    assert kwargs["block_type"] == "gate_checker"
    finalize_mock.assert_called_once()


def test_judge_falls_back_when_sonnet_errors() -> None:
    gpt = agreement_checker.ModelResult("gpt-4o", "ok\n【判定: GO】", "OK", "GO")
    sonnet = agreement_checker.ModelResult("sonnet", "", "ERROR", "ERROR", error="quota")
    decision = agreement_checker.judge(gpt, sonnet)
    assert decision.sonnet_available is False
    assert decision.final_judgment == "GO"
    assert "Sonnetフォールバック" in decision.adopted_model
