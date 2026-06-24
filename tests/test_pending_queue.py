"""pending_queue 保留キュー機能のテスト。

対象: common/ledger.py の enqueue_pending / fetch_pending_queue /
      mark_pending_done / expire_old_pending / count_pending_queue
      および reserve() の pending_queue 連携。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


# ──────────────────────────────────────────────────────────────
# enqueue / fetch / count
# ──────────────────────────────────────────────────────────────


def test_enqueue_pending_returns_id():
    from common.ledger import enqueue_pending

    row_id = enqueue_pending("classify", block_type="mail_classify", target_id="msg-001", script="mail_pipeline")
    assert isinstance(row_id, int)
    assert row_id > 0


def test_fetch_pending_queue_fifo():
    from common.ledger import enqueue_pending, fetch_pending_queue

    enqueue_pending("classify", target_id="msg-A", script="s")
    enqueue_pending("classify", target_id="msg-B", script="s")
    enqueue_pending("classify", target_id="msg-C", script="s")

    rows = fetch_pending_queue(phase="classify")
    assert len(rows) == 3
    assert [r["target_id"] for r in rows] == ["msg-A", "msg-B", "msg-C"]


def test_fetch_pending_queue_filters_by_phase():
    from common.ledger import enqueue_pending, fetch_pending_queue

    enqueue_pending("classify", target_id="mail-1", script="mail_pipeline")
    enqueue_pending("matching", target_id="case-1", script="matching_v3")

    classify_rows = fetch_pending_queue(phase="classify")
    matching_rows = fetch_pending_queue(phase="matching")

    assert len(classify_rows) == 1
    assert classify_rows[0]["target_id"] == "mail-1"
    assert len(matching_rows) == 1
    assert matching_rows[0]["target_id"] == "case-1"


def test_count_pending_queue():
    from common.ledger import count_pending_queue, enqueue_pending

    assert count_pending_queue() == 0
    enqueue_pending("classify", target_id="x")
    enqueue_pending("classify", target_id="y")
    enqueue_pending("matching", target_id="z")

    assert count_pending_queue() == 3
    assert count_pending_queue(phase="classify") == 2
    assert count_pending_queue(phase="matching") == 1


# ──────────────────────────────────────────────────────────────
# mark_pending_done
# ──────────────────────────────────────────────────────────────


def test_mark_pending_done():
    from common.ledger import count_pending_queue, enqueue_pending, fetch_pending_queue, mark_pending_done

    row_id = enqueue_pending("classify", target_id="done-me")
    assert count_pending_queue(phase="classify") == 1

    mark_pending_done(row_id)
    assert count_pending_queue(phase="classify") == 0

    rows = fetch_pending_queue(phase="classify")
    assert len(rows) == 0


def test_mark_pending_done_does_not_affect_others():
    from common.ledger import count_pending_queue, enqueue_pending, mark_pending_done

    r1 = enqueue_pending("classify", target_id="keep-me")
    r2 = enqueue_pending("classify", target_id="remove-me")

    mark_pending_done(r2)

    rows_left = count_pending_queue(phase="classify")
    assert rows_left == 1


# ──────────────────────────────────────────────────────────────
# expire_old_pending
# ──────────────────────────────────────────────────────────────


def test_expire_old_pending_does_not_expire_recent():
    from common.ledger import count_pending_queue, enqueue_pending, expire_old_pending

    enqueue_pending("classify", target_id="recent")
    expired = expire_old_pending(days=7)
    assert expired == 0
    assert count_pending_queue() == 1


def test_expire_old_pending_expires_stale(monkeypatch):
    """9日前のエントリが失効することを確認する。"""
    from common.state_store import begin_immediate

    # 9日前のタイムスタンプを直接挿入
    old_ts = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()
    with begin_immediate() as conn:
        conn.execute(
            "INSERT INTO pending_queue(phase, target_id, script, queued_at, status) VALUES(?,?,?,?,?)",
            ("classify", "stale-msg", "mail_pipeline", old_ts, "pending"),
        )

    from common.ledger import count_pending_queue, expire_old_pending

    assert count_pending_queue() == 1
    expired = expire_old_pending(days=7)
    assert expired == 1
    assert count_pending_queue() == 0


def test_expire_old_pending_keeps_done_entries(monkeypatch):
    """status='done' のエントリは expire 対象外。"""
    from common.state_store import begin_immediate

    old_ts = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()
    with begin_immediate() as conn:
        conn.execute(
            "INSERT INTO pending_queue(phase, target_id, script, queued_at, status) VALUES(?,?,?,?,?)",
            ("classify", "done-entry", "test", old_ts, "done"),
        )

    from common.ledger import expire_old_pending

    expired = expire_old_pending(days=7)
    assert expired == 0


# ──────────────────────────────────────────────────────────────
# reserve() → pending_queue 連携
# ──────────────────────────────────────────────────────────────


def test_reserve_over_limit_enqueues_pending(monkeypatch):
    """DAILY_CALL_LIMIT=0 で reserve() が None を返し pending_queue にエントリが追加される。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "0")
    monkeypatch.setenv("DAILY_CALL_LIMIT_RESEARCH", "0")
    from common.ledger import count_pending_queue, fetch_pending_queue, reserve

    result = reserve("research", block_type="mail_classify", target_id="msg-x", script="mail_pipeline")
    assert result is None
    assert count_pending_queue(phase="research") == 1

    rows = fetch_pending_queue(phase="research")
    assert rows[0]["target_id"] == "msg-x"
    assert rows[0]["block_type"] == "mail_classify"
    assert rows[0]["script"] == "mail_pipeline"


def test_reserve_over_limit_enqueues_without_optional_args(monkeypatch):
    """オプション引数なしでも pending_queue に登録される（target_id="" のエントリ）。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "0")
    monkeypatch.setenv("DAILY_CALL_LIMIT_RESEARCH", "0")
    from common.ledger import count_pending_queue, reserve

    result = reserve("research")
    assert result is None
    assert count_pending_queue(phase="research") == 1


def test_reserve_under_limit_does_not_enqueue(monkeypatch):
    """上限未達のとき pending_queue には追加されない。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "5")
    from common.ledger import count_pending_queue, release, reserve

    rid = reserve("research", block_type="mail_classify", target_id="msg-ok", script="s")
    assert rid is not None
    assert count_pending_queue(phase="research") == 0
    release(rid)


# ──────────────────────────────────────────────────────────────
# allowed() → pending_queue 連携（cost_guard.py）
# ──────────────────────────────────────────────────────────────


def _mock_select(monkeypatch, model="gpt-4o-mini", cls="light"):
    from common.model_selector import ModelSelection

    monkeypatch.setattr(
        "common.model_selector.select_model", lambda p, model_hint=None: ModelSelection(model, cls, False, False)
    )


def test_allowed_stopped_call_limit_enqueues(monkeypatch):
    """allowed() で stopped_call_limit 時に pending_queue にエントリが追加される。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "0")
    monkeypatch.setenv("DAILY_CALL_LIMIT_RESEARCH", "0")
    _mock_select(monkeypatch)
    import cost_guard as cg
    from common.ledger import count_pending_queue, fetch_pending_queue

    d = cg.allowed(
        phase="research",
        block_type="mail_classify",
        target_id="test-target-123",
        est_in=100,
        est_out=100,
        script="mail_pipeline",
    )
    assert d.allowed is False
    assert d.reason == cg.Reasons.stopped_call_limit

    assert count_pending_queue(phase="research") == 1
    rows = fetch_pending_queue(phase="research")
    assert rows[0]["target_id"] == "test-target-123"
    assert rows[0]["block_type"] == "mail_classify"
    assert rows[0]["script"] == "mail_pipeline"


def test_has_pending_target():
    from common.ledger import enqueue_pending, has_pending_target

    assert has_pending_target("classify", "msg-dup") is False
    enqueue_pending("classify", target_id="msg-dup", script="mail_pipeline")
    assert has_pending_target("classify", "msg-dup") is True
    assert has_pending_target("matching", "msg-dup") is False


def test_prioritize_pending_work_items_moves_queued_first():
    from mail_pipeline.mail_pipeline import _prioritize_pending_work_items
    from common.ledger import enqueue_pending

    enqueue_pending("classify", target_id="msg-b", script="mail_pipeline")
    items = [
        {"msg_id": "msg-a"},
        {"msg_id": "msg-b"},
        {"msg_id": "msg-c"},
    ]
    pending_by_target = _prioritize_pending_work_items(items, phase="classify")
    assert [item["msg_id"] for item in items] == ["msg-b", "msg-a", "msg-c"]
    assert pending_by_target["msg-b"] > 0
