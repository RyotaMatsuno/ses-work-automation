"""8.3 DAILY_CALL_LIMIT 予約方式のテスト（SPEC §3.2）。"""

from __future__ import annotations


def _mock_select(monkeypatch, model="gpt-4o-mini", cls="light"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model", lambda p, model_hint=None: ModelSelection(model, cls, False, False)
    )


def test_reserve_under_limit(monkeypatch):
    """デフォルト上限30に達する前は reserve が成功する。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "5")
    from common.ledger import release, reserve

    ids = []
    for i in range(5):
        rid = reserve("research")
        assert rid is not None, f"reserve failed at {i}"
        ids.append(rid)
    # 上限到達
    assert reserve("research") is None
    # cleanup
    for rid in ids:
        release(rid)


def test_reserve_at_limit_returns_none(monkeypatch):
    """DAILY_CALL_LIMIT_DEFAULT=1 のとき2回目は None。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "1")
    from common.ledger import release, reserve

    rid = reserve("research")
    assert rid is not None
    assert reserve("research") is None
    release(rid)


def test_release_frees_slot(monkeypatch):
    """release 後は再 reserve できる。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "1")
    from common.ledger import release, reserve

    rid = reserve("research")
    assert rid is not None
    release(rid)
    rid2 = reserve("research")
    assert rid2 is not None
    release(rid2)


def test_per_phase_limit(monkeypatch):
    """DAILY_CALL_LIMIT_IMPLEMENTATION=2 のとき implementation は2回まで。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_IMPLEMENTATION", "2")
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "100")
    from common.ledger import release, reserve

    r1 = reserve("implementation")
    r2 = reserve("implementation")
    assert r1 is not None
    assert r2 is not None
    assert reserve("implementation") is None
    # research は別カウンタ
    rr = reserve("research")
    assert rr is not None
    release(r1)
    release(r2)
    release(rr)


def test_allowed_stops_call_limit(monkeypatch):
    """allowed() で DAILY_CALL_LIMIT 超過時に reason=stopped_call_limit。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "0")
    _mock_select(monkeypatch)
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", est_in=100, est_out=100, script="test")
    assert d.allowed is False
    assert d.reason == cg.Reasons.stopped_call_limit
    assert d.exit_code == 1
