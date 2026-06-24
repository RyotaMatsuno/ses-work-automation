"""Task BA: matching_batch / matching_pipeline の CostGuard フェーズ分離テスト。"""

from __future__ import annotations

import sys
def test_call_limit_matching_batch_uses_env(monkeypatch):
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_BATCH", "40")
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING", "60")
    from common.ledger import _call_limit

    assert _call_limit("matching_batch") == 40


def test_call_limit_matching_pipeline_uses_env(monkeypatch):
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_PIPELINE", "30")
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING", "60")
    from common.ledger import _call_limit

    assert _call_limit("matching_pipeline") == 30


def test_call_limit_matching_batch_falls_back_to_legacy(monkeypatch):
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_BATCH", "0")
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING", "55")
    from common.ledger import _call_limit

    assert _call_limit("matching_batch") == 55


def test_matching_batch_pipeline_isolation(monkeypatch):
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_BATCH", "1")
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_PIPELINE", "5")
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING", "60")
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "100")
    from common.ledger import release, reserve

    batch_rid = reserve("matching_batch", target_id="case-1", script="matching_v3")
    assert batch_rid is not None
    assert reserve("matching_batch", target_id="case-2", script="matching_v3") is None

    pipeline_rid = reserve("matching_pipeline", target_id="mail-1", script="mail_pipeline")
    assert pipeline_rid is not None

    release(batch_rid)
    release(pipeline_rid)


def _mock_select(monkeypatch, model="gpt-4o-mini", cls="light"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model", lambda p, model_hint=None: ModelSelection(model, cls, False, False)
    )


def test_allowed_matching_pipeline_uses_separate_phase(monkeypatch):
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_BATCH", "1")
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_PIPELINE", "5")
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING", "60")
    _mock_select(monkeypatch)
    import cost_guard as cg
    from common.ledger import count_pending_queue, release, reserve

    batch_rid = reserve("matching_batch", target_id="batch-only")
    assert batch_rid is not None
    assert reserve("matching_batch", target_id="batch-only-2") is None
    release(batch_rid)

    decision = cg.allowed(
        phase="matching_pipeline",
        block_type="ai_matching",
        target_id="proj-2",
        est_in=100,
        est_out=100,
        script="mail_pipeline",
    )
    assert decision.allowed is True
    assert count_pending_queue(phase="matching_pipeline") == 0


def test_matching_v3_cost_guard_uses_matching_batch_phase(monkeypatch, tmp_path):
    monkeypatch.setenv("DAILY_CALL_LIMIT_MATCHING_BATCH", "5")
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "100")

    class _Decision:
        allowed = True
        model = "gpt-4.1-nano"
        reservation_id = "rid-test"

    import importlib.util
    from pathlib import Path

    monkeypatch.setattr("cost_guard.allowed", lambda **kwargs: _Decision())
    monkeypatch.setattr("cost_guard.finalize", lambda *args, **kwargs: None)

    matching_guard_path = Path(__file__).resolve().parents[1] / "matching_v3" / "cost_guard.py"
    spec = importlib.util.spec_from_file_location("matching_v3_cost_guard_ba", matching_guard_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    guard = mod.CostGuard(tmp_path / "cost.jsonl")
    assert guard.can_call(100, 100, target_id="case-abc") is True
    assert mod.MATCHING_BATCH_PHASE == "matching_batch"
