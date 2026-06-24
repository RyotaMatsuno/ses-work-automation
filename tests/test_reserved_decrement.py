"""8.17 成功/permanent 失敗時に phase_calls.reserved が -1 されることを確認（SPEC §3.2.1）。"""

from __future__ import annotations

from datetime import datetime, timezone

from common.state_store import init_schema, open_conn


def _get_phase_calls(phase: str) -> dict:
    init_schema()
    conn = open_conn()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT reserved, consumed FROM phase_calls WHERE date=? AND phase=?", (today, phase)
        ).fetchone()
        return {"reserved": row["reserved"], "consumed": row["consumed"]} if row else {"reserved": 0, "consumed": 0}
    finally:
        conn.close()


def _make_decision(monkeypatch, target_id="proj-decrement-001"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="skill_judge", target_id=target_id, script="test")
    assert d.allowed
    return d


def test_reserved_decrements_on_success(monkeypatch):
    """成功時: reserved -= 1, consumed += 1。"""
    import cost_guard as cg

    d = _make_decision(monkeypatch)

    before = _get_phase_calls("research")
    assert before["reserved"] == 1

    cg.finalize(d, in_tokens=100, out_tokens=50, success=True)

    after = _get_phase_calls("research")
    assert after["reserved"] == 0
    assert after["consumed"] == 1


def test_reserved_decrements_on_permanent(monkeypatch):
    """permanent 失敗時: reserved -= 1, consumed += 1（エラー記録あり）。"""
    import cost_guard as cg

    d = _make_decision(monkeypatch, target_id="proj-decrement-002")

    before = _get_phase_calls("research")
    assert before["reserved"] >= 1

    cg.finalize(d, in_tokens=100, out_tokens=50, success=False, error_kind="permanent_api")

    after = _get_phase_calls("research")
    # consumed は増えていて、reserved は減っている
    assert after["reserved"] == before["reserved"] - 1
    assert after["consumed"] == before["consumed"] + 1


def test_reserved_decrements_on_transient(monkeypatch):
    """transient 失敗時: reserved -= 1, consumed は変わらない。"""
    import cost_guard as cg

    d = _make_decision(monkeypatch, target_id="proj-decrement-003")

    before = _get_phase_calls("research")
    cg.finalize(d, success=False, error_kind="transient")

    after = _get_phase_calls("research")
    assert after["reserved"] == before["reserved"] - 1
    assert after["consumed"] == before["consumed"]
