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


def _cg_allowed_ok() -> mock.Mock:
    decision = mock.Mock()
    decision.exit_code = 0
    decision.allowed = True
    return decision


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
        with mock.patch.object(agreement_checker, "_cg_allowed", return_value=_cg_allowed_ok()):
            result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "ERROR"
    assert "403" in result.error
    assert any("403" in rec.message for rec in caplog.records)


def test_call_sonnet_finalizes_costguard() -> None:
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
        with mock.patch.object(agreement_checker, "_cg_allowed", return_value=_cg_allowed_ok()):
            with mock.patch.object(agreement_checker, "_cg_finalize") as finalize_mock:
                result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "OK"
    finalize_mock.assert_called_once()
    kwargs = finalize_mock.call_args[1]
    assert kwargs["in_tokens"] == 120
    assert kwargs["out_tokens"] == 80
    assert kwargs["success"] is True


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
        with mock.patch.object(agreement_checker, "_cg_allowed", return_value=fake_decision) as allowed_mock:
            with mock.patch.object(agreement_checker, "_cg_finalize") as finalize_mock:
                result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "OK"
    allowed_mock.assert_called_once()
    kwargs = allowed_mock.call_args[1]
    assert kwargs["phase"] == "review_sonnet"
    assert kwargs["block_type"] == "gate_check"
    finalize_mock.assert_called_once()


def test_judge_falls_back_when_sonnet_errors() -> None:
    gpt = agreement_checker.ModelResult("gpt-4o", "ok\n【判定: GO】", "OK", "GO")
    sonnet = agreement_checker.ModelResult("sonnet", "", "ERROR", "ERROR", error="quota")
    decision = agreement_checker.judge(gpt, sonnet)
    assert decision.sonnet_available is False
    assert decision.final_judgment == "GO"
    assert "Sonnetフォールバック" in decision.adopted_model


def test_run_gate_check_exits_2_when_ledger_can_spend_false(tmp_path: Path) -> None:
    """ledger.can_spend()=False のとき exit code 2 を返す（Layer1 CostGuard）。"""
    spec = tmp_path / "SPEC.md"
    spec.write_text("# dummy spec for test", encoding="utf-8")

    mock_ledger = mock.MagicMock()
    mock_ledger.can_spend.return_value = False

    with mock.patch.object(gate_check, "_LEDGER_AVAILABLE", True), \
         mock.patch.object(gate_check, "_ledger", mock_ledger), \
         mock.patch.object(gate_check, "_load_env", return_value={"OPENAI_API_KEY": "test-key"}), \
         mock.patch.object(gate_check, "check_daily_limit", return_value=(True, 0)), \
         mock.patch.object(gate_check, "save_result"):
        rc = gate_check.run_gate_check("requirements", str(spec), None, None)

    assert rc == 2
    mock_ledger.can_spend.assert_called()


def test_call_gpt4o_simple_blocks_when_ledger_can_spend_false() -> None:
    """call_gpt4o_simple: ledger.can_spend()=False で LedgerBlocked を返す。"""
    with mock.patch.object(agreement_checker, "_LEDGER_AVAILABLE", True), \
         mock.patch.object(agreement_checker, "_ledger") as mock_ledger, \
         mock.patch.object(agreement_checker, "_ledger_can_spend", return_value=False):
        result = agreement_checker.call_gpt4o_simple("sys", "user", "dummy-key")

    assert result.verdict == "ERROR"
    assert agreement_checker.LEDGER_BLOCKED_MARKER in result.error


def test_call_sonnet_blocks_when_ledger_can_spend_false() -> None:
    """call_sonnet: ledger.can_spend()=False で LedgerBlocked を返す。"""
    with mock.patch.object(agreement_checker, "_LEDGER_AVAILABLE", True), \
         mock.patch.object(agreement_checker, "_ledger_can_spend", return_value=False):
        result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "ERROR"
    assert agreement_checker.LEDGER_BLOCKED_MARKER in result.error


def test_sonnet_timeout_does_not_retry() -> None:
    """URLError（タイムアウト）時はリトライせず1回でERRORを返す。"""
    timeout_error = urllib.error.URLError("timed out")

    with mock.patch("urllib.request.urlopen", side_effect=timeout_error) as urlopen_mock:
        with mock.patch.object(agreement_checker, "_cg_allowed", return_value=_cg_allowed_ok()):
            with mock.patch.object(agreement_checker, "_ledger_can_spend", return_value=True):
                result = agreement_checker.call_sonnet("sys", "user", "dummy-key")

    assert result.verdict == "ERROR"
    assert urlopen_mock.call_count == 1


def test_call_gpt4o_simple_records_ledger_on_success() -> None:
    """call_gpt4o_simple: API成功後に ledger.record を呼ぶ。"""
    response_data = {
        "choices": [{"message": {"content": "問題なし\n【判定: GO】"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
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
        with mock.patch.object(agreement_checker, "_cg_allowed", return_value=_cg_allowed_ok()):
            with mock.patch.object(agreement_checker, "_ledger_can_spend", return_value=True):
                with mock.patch.object(agreement_checker, "_ledger_record") as record_mock:
                    result = agreement_checker.call_gpt4o_simple("sys", "user", "dummy-key")

    assert result.verdict == "OK"
    record_mock.assert_called_once_with(100, 50, "gpt-4o")
