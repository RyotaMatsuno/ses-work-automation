# -*- coding: utf-8 -*-
"""raw_inbox SQLite storage tests."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline import raw_inbox as ri


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "raw_inbox.db"


def test_init_db_creates_table_and_view(db_path):
    ri.init_db(db_path)
    conn = ri.get_connection(db_path)
    try:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')").fetchall()
        }
        assert "raw_emails" in tables
        assert "monthly_stats" in tables
    finally:
        conn.close()


def test_insert_raw_email_and_hash(db_path):
    inserted = ri.insert_raw_email(
        message_id="<test-1@example.com>",
        account="sessales",
        received_at="2026-06-18T10:00:00",
        sender="sender@example.com",
        subject="【案件】Java",
        body_text="本文テスト",
        has_attachment=False,
        attachment_names=[],
        db_path=db_path,
    )
    assert inserted is True
    inserted_again = ri.insert_raw_email(
        message_id="<test-1@example.com>",
        account="sessales",
        received_at="2026-06-18T10:00:00",
        sender="sender@example.com",
        subject="【案件】Java",
        body_text="本文テスト",
        db_path=db_path,
    )
    assert inserted_again is False
    assert ri.count_rows(db_path) == 1


def test_mark_processed_and_load(db_path):
    ri.insert_raw_email(
        message_id="<test-2@example.com>",
        account="matsuno",
        received_at="2026-06-18T11:00:00",
        sender="a@b.com",
        subject="件名",
        body_text="body",
        db_path=db_path,
    )
    ri.mark_processed("<test-2@example.com>", classify_result="project", db_path=db_path)
    processed = ri.load_processed_ids(db_path)
    assert "<test-2@example.com>" in processed
    assert ri.count_processed(db_path) == 1


def test_migrate_processed_ids_json(tmp_path, db_path):
    src = tmp_path / "processed_ids.json"
    ids = [f"<msg-{i}@example.com>" for i in range(1535)]
    src.write_text(json.dumps(ids, ensure_ascii=False), encoding="utf-8")

    migrated = ri.migrate_processed_ids_json(
        processed_path=src,
        db_path=db_path,
        backup_path=tmp_path / "processed_ids.json.bak",
    )
    assert migrated == 1535
    assert not src.exists()
    assert (tmp_path / "processed_ids.json.bak").exists()
    assert ri.count_processed(db_path) == 1535


def test_monthly_stats_view(db_path):
    ri.insert_raw_email(
        message_id="<a@x>",
        account="sessales",
        received_at="2026-06-01T09:00:00",
        sender="s",
        subject="s1",
        body_text="b",
        db_path=db_path,
    )
    ri.insert_raw_email(
        message_id="<b@x>",
        account="sessales",
        received_at="2026-06-15T09:00:00",
        sender="s",
        subject="s2",
        body_text="b",
        db_path=db_path,
    )
    ri.mark_processed("<a@x>", classify_result="project", db_path=db_path)
    ri.mark_processed("<b@x>", classify_result="skip", db_path=db_path)
    rows = ri.monthly_stats_rows(db_path)
    assert any(r["month"] == "2026-06" and r["classify_result"] == "project" for r in rows)
    assert any(r["month"] == "2026-06" and r["classify_result"] == "skip" for r in rows)


def test_fetch_unprocessed_from_db_prioritizes_fresh_over_other(db_path):
    ri.insert_raw_email(
        message_id="<other@x>",
        account="sessales",
        received_at="2026-06-19T10:00:00",
        sender="sales@example.com",
        subject="other件名",
        body_text="body",
        db_path=db_path,
    )
    ri.update_classify_result("<other@x>", "other", db_path=db_path)
    ri.insert_raw_email(
        message_id="<fresh@x>",
        account="sessales",
        received_at="2026-06-19T10:01:00",
        sender="sales@example.com",
        subject="fresh件名",
        body_text="body",
        db_path=db_path,
    )

    fresh_items, reclass_items = ri.fetch_unprocessed_from_db(limit=10, db_path=db_path)
    rows = fresh_items + reclass_items

    assert [row["msg_id"] for row in rows] == ["<fresh@x>", "<other@x>"]


def test_account_key_from_user():
    assert ri.account_key_from_user("sessales@terra-ltd.co.jp") == "sessales"
    assert ri.account_key_from_user("r-matsuno@terra-ltd.co.jp") == "matsuno"
    assert ri.account_key_from_user("r-okamoto@terra-ltd.co.jp") == "okamoto"


def test_retry_count_increment_and_get(db_path):
    ri.insert_raw_email(
        message_id="<retry@x>",
        account="sessales",
        received_at="2026-06-18T12:00:00",
        sender="s",
        subject="件名",
        body_text="body",
        db_path=db_path,
    )
    assert ri.get_retry_count("<retry@x>", db_path=db_path) == 0
    assert ri.increment_retry_count("<retry@x>", db_path=db_path) == 1
    assert ri.increment_retry_count("<retry@x>", db_path=db_path) == 2
    assert ri.get_retry_count("<retry@x>", db_path=db_path) == 2


def test_sqlite_wal_mode_enabled(db_path):
    ri.init_db(db_path)
    conn = ri.get_connection(db_path)
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
    finally:
        conn.close()


def test_concurrent_writes_do_not_raise(db_path):
    import threading

    ri.init_db(db_path)
    errors: list[Exception] = []

    def writer(idx: int) -> None:
        try:
            ri.insert_raw_email(
                message_id=f"<concurrent-{idx}@example.com>",
                account="sessales",
                received_at="2026-06-19T10:00:00",
                sender="s",
                subject=f"subject-{idx}",
                body_text=f"body-{idx}",
                db_path=db_path,
            )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert ri.count_rows(db_path) == 10


def _insert(db_path, msg_id, subject="件名", classify_result=None, processed=0):
    ri.insert_raw_email(
        message_id=msg_id,
        account="sessales",
        received_at="2026-06-19T10:00:00",
        sender="sender@example.com",
        subject=subject,
        body_text="body text",
        db_path=db_path,
    )
    if classify_result is not None or processed:
        conn = ri.get_connection(db_path)
        conn.execute(
            "UPDATE raw_emails SET classify_result=?, processed=? WHERE message_id=?",
            (classify_result, processed, msg_id),
        )
        conn.commit()
        conn.close()


def test_fetch_unprocessed_from_db_returns_limit(db_path):
    for i in range(5):
        _insert(db_path, f"<msg-{i}@x>")
    fresh_items, reclass_items = ri.fetch_unprocessed_from_db(limit=3, db_path=db_path)
    assert len(fresh_items) + len(reclass_items) == 3


def test_fetch_unprocessed_from_db_fresh_before_reclass(db_path):
    _insert(db_path, "<other-1@x>", classify_result="other")
    _insert(db_path, "<other-2@x>", classify_result="other")
    _insert(db_path, "<fresh-1@x>")
    fresh_items, reclass_items = ri.fetch_unprocessed_from_db(limit=10, db_path=db_path)
    assert len(fresh_items) > 0 and fresh_items[0]["classify_result"] is None, "freshが先頭に来るべき"
    assert reclass_items[0]["classify_result"] == "other"
    assert reclass_items[1]["classify_result"] == "other"


def test_fetch_unprocessed_from_db_dict_structure(db_path):
    _insert(db_path, "<struct-test@x>", subject="テスト件名")
    fresh_items, reclass_items = ri.fetch_unprocessed_from_db(limit=1, db_path=db_path)
    assert len(fresh_items) == 1
    em = fresh_items[0]
    assert em["msg_id"] == "<struct-test@x>"
    assert em["subject"] == "テスト件名"
    assert em["body"] == "body text"
    assert em["sender"] == "sender@example.com"
    assert em["reply_to"] == em["sender"]
    assert em["attachments"] == []
    assert em["_source"] == "db_backlog"
    assert em["classify_result"] is None
    assert isinstance(em["retry_count"], int)


def test_fetch_unprocessed_excludes_processed(db_path):
    _insert(db_path, "<done@x>", processed=1)
    _insert(db_path, "<todo@x>")
    fresh_items, reclass_items = ri.fetch_unprocessed_from_db(limit=10, db_path=db_path)
    msg_ids = [em["msg_id"] for em in fresh_items + reclass_items]
    assert "<todo@x>" in msg_ids
    assert "<done@x>" not in msg_ids
