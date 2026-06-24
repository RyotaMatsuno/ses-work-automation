# -*- coding: utf-8 -*-
"""CostGuard テストモード統合テスト（Task BD）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from common import state_store as ss
from common.ledger import (
    _call_limit,
    _usd_limit,
    can_spend,
    check_daily_limit,
    count_pending_queue,
    enqueue_pending,
    expire_old_pending,
    fetch_pending_queue,
    mark_pending_done,
    record,
    release,
    reserve,
)


@pytest.fixture(autouse=True)
def costguard_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """テストモード用の環境変数を設定する。"""
    monkeypatch.setenv("COSTGUARD_TEST_MODE", "true")
    monkeypatch.setenv("TEST_DAILY_LIMIT_USD", "0.10")
    monkeypatch.setenv("TEST_MONTHLY_LIMIT_USD", "0.50")
    monkeypatch.setenv("TEST_CALL_LIMIT_MATCHING_BATCH", "3")
    monkeypatch.setenv("TEST_CALL_LIMIT_MATCHING_PIPELINE", "3")
    monkeypatch.setenv("TEST_CALL_LIMIT_CLASSIFY", "5")


def _reserve_and_finalize(phase: str, target_id: str = "t") -> str:
    rid = reserve(phase, target_id=target_id, script="test")
    assert rid is not None
    record(10, 10, "gpt-4.1-nano", "test", phase=phase, reservation_id=rid)
    return rid


# ── レベル1: ユニットテスト ──────────────────────────────────────


def test_test_mode_uses_isolated_db(isolated_state_dir) -> None:
    """テストモードでは state_test.sqlite3 を使用し本番 DB と分離される。"""
    ss.init_schema()
    assert ss.get_db_path().name == "state_test.sqlite3"
    assert ss.get_db_path().parent == isolated_state_dir


def test_call_limit_uses_test_env() -> None:
    assert _call_limit("matching_batch") == 3
    assert _call_limit("matching_pipeline") == 3
    assert _call_limit("classify") == 5


def test_usd_limit_uses_test_env() -> None:
    assert _usd_limit("daily") == pytest.approx(0.10)
    assert _usd_limit("monthly") == pytest.approx(0.50)


def test_call_limit_blocks_at_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """CALL_LIMIT=3 で 4 回目がブロックされる。"""
    monkeypatch.setenv("TEST_CALL_LIMIT_CLASSIFY", "3")

    for i in range(3):
        _reserve_and_finalize("classify", target_id=f"msg-{i}")

    assert check_daily_limit("classify") is False
    assert reserve("classify", target_id="msg-blocked") is None


def test_call_limit_pending_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    """ブロック時に pending_queue へ投入される。"""
    monkeypatch.setenv("TEST_CALL_LIMIT_CLASSIFY", "1")
    _reserve_and_finalize("classify", target_id="first")

    result = reserve("classify", block_type="mail_classify", target_id="blocked-msg", script="mail_pipeline")
    assert result is None
    assert count_pending_queue(phase="classify") == 1

    rows = fetch_pending_queue(phase="classify")
    assert rows[0]["target_id"] == "blocked-msg"
    assert rows[0]["block_type"] == "mail_classify"


def test_usd_daily_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """日次 $0.10 超過時に can_spend が False を返す。"""
    monkeypatch.setenv("TEST_DAILY_LIMIT_USD", "0.10")
    # gpt-4.1-nano: 900k in tokens ≈ $0.09
    record(900_000, 0, "gpt-4.1-nano", "test", phase="classify")

    assert can_spend(est_in=100_000, est_out=100_000, model="gpt-4.1-nano") is False


def test_usd_monthly_blocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """月次 $0.50 超過時に can_spend が False を返す。"""
    monkeypatch.setenv("TEST_MONTHLY_LIMIT_USD", "0.50")
    # 4.5M in tokens ≈ $0.45
    record(4_500_000, 0, "gpt-4.1-nano", "test", phase="classify")

    assert can_spend(est_in=1_000_000, est_out=0, model="gpt-4.1-nano") is False


# ── レベル2: 統合テスト ──────────────────────────────────────────


def test_matching_batch_pipeline_isolation() -> None:
    """batch 上限到達でも pipeline はブロックされない。"""
    for i in range(3):
        _reserve_and_finalize("matching_batch", target_id=f"batch-{i}")

    assert reserve("matching_batch", target_id="batch-blocked") is None
    assert check_daily_limit("matching_batch") is False

    rid = reserve("matching_pipeline", target_id="pipeline-ok")
    assert rid is not None
    release(rid)


def test_pending_queue_fifo() -> None:
    """キュー投入順に FIFO で取得される。"""
    enqueue_pending("classify", target_id="msg-A", script="s")
    enqueue_pending("classify", target_id="msg-B", script="s")
    enqueue_pending("classify", target_id="msg-C", script="s")

    rows = fetch_pending_queue(phase="classify")
    assert [r["target_id"] for r in rows] == ["msg-A", "msg-B", "msg-C"]


def test_pending_queue_fifo_processing() -> None:
    """FIFO 順に mark_pending_done できる。"""
    ids = [
        enqueue_pending("classify", target_id="first"),
        enqueue_pending("classify", target_id="second"),
    ]
    rows = fetch_pending_queue(phase="classify")
    assert rows[0]["id"] == ids[0]

    mark_pending_done(ids[0])
    rows = fetch_pending_queue(phase="classify")
    assert len(rows) == 1
    assert rows[0]["target_id"] == "second"


def test_pending_expire() -> None:
    """7 日経過で status=expired になる。"""
    old_ts = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()
    with ss.begin_immediate() as conn:
        conn.execute(
            "INSERT INTO pending_queue(phase, target_id, script, queued_at, status) VALUES(?,?,?,?,?)",
            ("classify", "stale-msg", "mail_pipeline", old_ts, "pending"),
        )

    assert count_pending_queue() == 1
    expired = expire_old_pending(days=7)
    assert expired == 1
    assert count_pending_queue() == 0


# ── レベル3: フェーズ分離テスト ──────────────────────────────────


def test_phase_separation() -> None:
    """matching_batch と matching_pipeline が独立した上限で動作する。"""
    assert _call_limit("matching_batch") == 3
    assert _call_limit("matching_pipeline") == 3

    for i in range(3):
        _reserve_and_finalize("matching_batch", target_id=f"b-{i}")

    assert reserve("matching_batch", target_id="b-extra") is None

    rid = reserve("matching_pipeline", target_id="p-1")
    assert rid is not None
    _reserve_and_finalize("matching_pipeline", target_id="p-2")
    release(rid)
