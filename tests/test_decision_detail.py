"""8.21 error_internal 時に Decision.detail に lock_timeout 等が設定される（SPEC §7.1）。"""

from __future__ import annotations


def test_lock_timeout_sets_detail(isolated_state_dir, monkeypatch):
    """lock_timeout が発生すると Decision.detail == "lock_timeout"。"""
    monkeypatch.setenv("SQLITE_TIMEOUT_SEC", "0")

    from common.state_store import init_schema, open_conn

    init_schema()

    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )

    blocker = open_conn()
    blocker.execute("BEGIN IMMEDIATE")

    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="test")

    blocker.execute("ROLLBACK")
    blocker.close()

    assert d.reason == cg.Reasons.error_internal
    assert d.detail == "lock_timeout"
    assert d.script == "test"


def test_detail_empty_on_success(monkeypatch):
    """成功時は Decision.detail が空文字列。"""
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model",
        lambda p, model_hint=None: ModelSelection("gpt-4o-mini", "light", False, False),
    )
    import cost_guard as cg

    d = cg.allowed(phase="research", block_type="manual_query", script="test")
    if d.allowed:
        assert d.detail == ""
