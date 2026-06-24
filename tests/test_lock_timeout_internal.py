"""8.18 BEGIN IMMEDIATE timeout=5s → reason=error_internal, detail=lock_timeout。"""

from __future__ import annotations

import sqlite3

import pytest


def test_lock_timeout_in_reserve(isolated_state_dir, monkeypatch):
    """sqlite が OperationalError(database is locked) を返す場合に reserve が例外を raise。"""
    from common.state_store import init_schema, open_conn

    init_schema()

    # 別の接続で BEGIN IMMEDIATE をホールドしてロックを占有
    blocker = open_conn()
    blocker.execute("BEGIN IMMEDIATE")

    # timeout=0 の接続で reserve を呼ぶと OperationalError が発生する
    monkeypatch.setenv("SQLITE_TIMEOUT_SEC", "0")

    from common.ledger import reserve

    with pytest.raises(sqlite3.OperationalError):
        reserve("research")

    blocker.execute("ROLLBACK")
    blocker.close()


def test_lock_timeout_in_allowed(isolated_state_dir, monkeypatch):
    """allowed() 内で OperationalError が発生すると reason=error_internal, detail=lock_timeout。"""
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

    assert d.allowed is False
    assert d.reason == cg.Reasons.error_internal
    assert d.detail == "lock_timeout"
    assert d.exit_code == 2
