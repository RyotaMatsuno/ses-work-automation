"""8.10 transient 失敗で予約が解放されることを確認（SPEC §3.2.1）。"""

from __future__ import annotations

from common.ledger import release, reserve


def test_transient_failure_releases_reservation(monkeypatch):
    """transient 失敗後は reserved -= 1 されて再 reserve できる。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "1")

    rid = reserve("research")
    assert rid is not None
    # 上限に達しているはず
    assert reserve("research") is None

    # transient 失敗 → release
    release(rid)

    # 解放後は再 reserve できる
    rid2 = reserve("research")
    assert rid2 is not None
    release(rid2)


def test_release_decrements_reserved_not_consumed():
    """release は reserved を -1 するが consumed は増やさない。"""
    from datetime import datetime, timezone

    from common.state_store import init_schema, open_conn

    init_schema()

    rid = reserve("design")
    assert rid is not None

    conn = open_conn()
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row_before = conn.execute(
            "SELECT reserved, consumed FROM phase_calls WHERE date=? AND phase=?", (today, "design")
        ).fetchone()
        assert row_before["reserved"] == 1
        assert row_before["consumed"] == 0
    finally:
        conn.close()

    release(rid)

    conn = open_conn()
    try:
        row_after = conn.execute(
            "SELECT reserved, consumed FROM phase_calls WHERE date=? AND phase=?", (today, "design")
        ).fetchone()
        assert row_after["reserved"] == 0
        assert row_after["consumed"] == 0  # consumed は増えていない
    finally:
        conn.close()
