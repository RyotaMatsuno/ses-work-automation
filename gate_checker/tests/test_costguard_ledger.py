"""CostGuard ledger 統合テスト（can_spend=False → exit code 2）。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

GATE_CHECKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE_CHECKER_DIR))
sys.path.insert(0, str(GATE_CHECKER_DIR.parent))

import agreement_checker
import gate_check


def test_call_gpt4o_raises_when_ledger_blocks() -> None:
    """gate_check.call_gpt4o: ledger.can_spend()=False で RuntimeError。"""
    mock_ledger = mock.MagicMock()
    mock_ledger.can_spend.return_value = False

    with mock.patch.object(gate_check, "_LEDGER_AVAILABLE", True), \
         mock.patch.object(gate_check, "_ledger", mock_ledger):
        with pytest.raises(RuntimeError, match="ledger"):
            gate_check.call_gpt4o("sys", "user prompt", "dummy-key")


def test_run_gate_check_exits_2_via_agreement_checker_ledger_block(tmp_path: Path) -> None:
    """run_gate_check: agreement_checker が LedgerBlocked を返したとき exit 2。"""
    spec = tmp_path / "SPEC.md"
    spec.write_text("# test", encoding="utf-8")

    blocked = agreement_checker.ModelResult(
        "gpt-4o", "", "ERROR", "ERROR",
        error=f"{agreement_checker.LEDGER_BLOCKED_MARKER}: ledger.can_spend()=False",
    )
    ok_sonnet = agreement_checker.ModelResult("sonnet", "ok\n【判定: GO】", "OK", "GO")
    decision = agreement_checker.AgreementDecision(
        final_verdict="OK",
        final_judgment="GO",
        adopted_model="gpt-4o",
        adopted_result=blocked,
        gpt_result=blocked,
        sonnet_result=ok_sonnet,
    )

    mock_ledger = mock.MagicMock()
    mock_ledger.can_spend.return_value = True

    with mock.patch.object(gate_check, "_LEDGER_AVAILABLE", True), \
         mock.patch.object(gate_check, "_ledger", mock_ledger), \
         mock.patch.object(gate_check, "check_daily_limit", return_value=(True, 0)), \
         mock.patch.object(gate_check, "_load_env", return_value={"OPENAI_API_KEY": "test-key"}), \
         mock.patch.object(gate_check, "run_dual_review", return_value=decision), \
         mock.patch.object(gate_check, "save_result") as save_mock:
        rc = gate_check.run_gate_check("requirements", str(spec), None, None)

    assert rc == 2
    save_mock.assert_called_once()
    payload = save_mock.call_args[0][0]
    assert payload["verdict"] == "COSTGUARD_BLOCKED"
