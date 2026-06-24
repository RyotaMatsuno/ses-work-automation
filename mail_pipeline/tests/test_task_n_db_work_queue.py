# -*- coding: utf-8 -*-
"""Task N: DB work queue + reclassification tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline import mail_pipeline as mp
from mail_pipeline import raw_inbox as ri


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "raw_inbox.db"


def _insert_unprocessed(
    db_path,
    message_id: str,
    subject: str,
    *,
    classify_result: str | None = None,
) -> None:
    ri.insert_raw_email(
        message_id=message_id,
        account="sessales",
        received_at="2026-06-19T10:00:00",
        sender="sales@example.com",
        subject=subject,
        body_text="本文",
        db_path=db_path,
    )
    if classify_result is not None:
        ri.update_classify_result(message_id, classify_result, db_path=db_path)


def test_fetch_unprocessed_from_db_returns_limit_and_order(db_path):
    _insert_unprocessed(db_path, "<other@x>", "【案件】再分類対象", classify_result="other")
    _insert_unprocessed(db_path, "<fresh@x>", "【案件】新着", classify_result=None)
    _insert_unprocessed(db_path, "<fresh2@x>", "【案件】新着2", classify_result=None)

    fresh_items, reclass_items = ri.fetch_unprocessed_from_db(limit=2, db_path=db_path)
    rows = fresh_items + reclass_items

    # limit=2 with 20% reclass ratio => fresh_quota=1, reclass_quota=1
    assert len(rows) == 2
    assert fresh_items[0]["msg_id"] == "<fresh@x>"
    assert reclass_items[0]["msg_id"] == "<other@x>"
    assert fresh_items[0]["classify_result"] is None
    assert fresh_items[0]["_source"] == "db_backlog"
    assert fresh_items[0]["reply_to"] == fresh_items[0]["sender"]
    assert fresh_items[0]["_queue_type"] == "fresh"
    assert reclass_items[0]["_queue_type"] == "reclass"


def test_fetch_unprocessed_from_db_includes_required_fields(db_path):
    _insert_unprocessed(db_path, "<one@x>", "件名テスト", classify_result=None)
    fresh_items, _ = ri.fetch_unprocessed_from_db(limit=1, db_path=db_path)
    row = fresh_items[0]

    for key in ("msg_id", "subject", "body", "sender", "_source"):
        assert key in row
    assert row["msg_id"] == "<one@x>"
    assert row["subject"] == "件名テスト"
    assert row["body"] == "本文"
    assert row["sender"] == "sales@example.com"


@patch("mail_pipeline.mail_pipeline.classify_email")
def test_reclassify_by_rule_project_promotes(mock_classify):
    mock_classify.return_value = {"type": "project", "name": "Java開発"}
    emails = [{"subject": "【案件情報】Java開発", "body": "案件本文", "sender": "sales@example.com"}]

    results, promoted = mp._reclassify_by_rule(emails)

    assert promoted == 1
    assert results[0]["type"] == "project"
    mock_classify.assert_called_once()


def test_reclassify_by_rule_engineer_is_skip():
    emails = [{"subject": "【人材情報】Java 30歳", "body": "人材本文", "sender": "sales@example.com"}]

    results, promoted = mp._reclassify_by_rule(emails)

    assert promoted == 0
    assert results[0]["type"] == "skip"


def test_reclassify_by_rule_seminar_is_skip():
    emails = [{"subject": "セミナーご案内", "body": "セミナー本文", "sender": "sales@example.com"}]

    results, promoted = mp._reclassify_by_rule(emails)

    assert promoted == 0
    assert results[0]["type"] == "skip"


@patch("mail_pipeline.mail_pipeline.get_available_engineers", return_value=[])
@patch("mail_pipeline.mail_pipeline._reclassify_by_rule", return_value=({0: {"type": "skip"}}, 0))
@patch("mail_pipeline.mail_pipeline.classify_email_v2", return_value={0: {"type": "skip", "note": "fresh"}})
@patch("mail_pipeline.mail_pipeline.fetch_unprocessed_from_db")
@patch("mail_pipeline.mail_pipeline.fetch_recent_emails", return_value=[])
@patch("mail_pipeline.mail_pipeline.ensure_project_db_properties")
@patch("mail_pipeline.mail_pipeline.ensure_raw_inbox_ready")
def test_main_body_uses_db_work_queue(
    mock_ready,
    mock_props,
    mock_fetch_imap,
    mock_fetch_db,
    mock_classify_v2,
    mock_reclassify,
    mock_engineers,
    db_path,
    monkeypatch,
):
    monkeypatch.setenv("DRY_RUN_PROCESS_EMAILS", "1")
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.setattr(mp, "RAW_INBOX_DB", db_path)

    fresh = {
        "msg_id": "<fresh@x>",
        "subject": "新着",
        "body": "b",
        "sender": "a@b.com",
        "reply_to": "a@b.com",
        "attachments": [],
        "classify_result": None,
        "_source": "db_backlog",
    }
    reclass = {
        "msg_id": "<other@x>",
        "subject": "再分類",
        "body": "b2",
        "sender": "a@b.com",
        "reply_to": "a@b.com",
        "attachments": [],
        "classify_result": "other",
        "_source": "db_backlog",
    }
    mock_fetch_db.return_value = ([fresh], [reclass])

    metrics = MagicMock()
    with patch.object(mp, "get_unprocessed_count", return_value=7):
        mp._main_body(metrics, fetch_limit=10, process_limit=5)

    mock_fetch_db.assert_called_once_with(limit=5, db_path=db_path)
    mock_classify_v2.assert_called_once()
    mock_reclassify.assert_called_once()
    metrics.set.assert_any_call("mails_fresh", 1)
    metrics.set.assert_any_call("mails_reclass", 1)
    metrics.set.assert_any_call("db_backlog_remaining", 7)
