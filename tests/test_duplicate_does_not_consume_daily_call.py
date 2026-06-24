"""8.9 重複 claim 時は日次呼び出し数を消費しないことを確認。"""

from __future__ import annotations

from common.ledger import check_daily_limit


def test_duplicate_does_not_consume_call(monkeypatch):
    """同一 key を2回 claim しても phase_calls は増えない（allowed が return せず reserve を呼ばない）。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "5")
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )

    import cost_guard as cg

    key_id = "proj-dup-001"

    # 1回目: 成功
    d1 = cg.allowed(phase="research", block_type="skill_judge", target_id=key_id, script="test")
    assert d1.allowed is True

    # 2回目: 同じ project_id → skipped_duplicate
    d2 = cg.allowed(phase="research", block_type="skill_judge", target_id=key_id, script="test")
    assert d2.reason == cg.Reasons.skipped_duplicate
    assert d2.allowed is False

    # reserve が呼ばれていないので phase_calls は増えていない
    # d1 は finalize せずに check_daily_limit で確認
    # reserved=1, consumed=0 → still under limit=5
    assert check_daily_limit("research") is True
