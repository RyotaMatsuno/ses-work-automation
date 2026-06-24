# -*- coding: utf-8 -*-
"""Task K: PROCESS_LIMIT=200 / CostGuard $8/day / backlog log tests."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline import mail_pipeline as mp
from mail_pipeline import raw_inbox as ri


def test_process_limit_is_200():
    assert mp.PROCESS_LIMIT == 200
    assert mp.PROCESS_LIMIT == mp.FETCH_LIMIT


def test_count_unprocessed_excludes_processed(db_path):
    ri.insert_raw_email(
        message_id="<unprocessed@example.com>",
        account="sessales",
        received_at="2026-06-19T10:00:00",
        sender="a@b.com",
        subject="未処理",
        body_text="body",
        db_path=db_path,
    )
    ri.insert_raw_email(
        message_id="<processed@example.com>",
        account="sessales",
        received_at="2026-06-19T10:01:00",
        sender="a@b.com",
        subject="処理済",
        body_text="body",
        db_path=db_path,
    )
    ri.mark_processed("<processed@example.com>", classify_result="skip", db_path=db_path)

    assert ri.count_unprocessed(db_path) == 1
    assert ri.count_processed(db_path) == 1


def test_get_unprocessed_count_uses_raw_inbox_db(db_path, monkeypatch):
    monkeypatch.setattr(mp, "RAW_INBOX_DB", db_path)
    ri.insert_raw_email(
        message_id="<backlog@example.com>",
        account="sessales",
        received_at="2026-06-19T11:00:00",
        sender="a@b.com",
        subject="バックログ",
        body_text="body",
        db_path=db_path,
    )

    assert mp.get_unprocessed_count() == 1


@patch("mail_pipeline.mail_pipeline.can_spend", return_value=False)
def test_batch_budget_blocked_at_daily_8_usd(mock_can_spend):
    batch_items = [
        {
            "custom_id": "classify_0",
            "params": {
                "messages": [{"content": "x" * 4000}],
                "system": "system",
                "max_tokens": 50,
            },
        }
    ]

    assert mp._batch_budget_allowed(batch_items, phase="classify") is False
    mock_can_spend.assert_called_once()


@patch("mail_pipeline.mail_pipeline.finalize")
@patch("mail_pipeline.mail_pipeline.allowed")
def test_call_claude_blocked_when_daily_budget_exceeded(mock_allowed, mock_finalize):
    mock_allowed.return_value = SimpleNamespace(
        allowed=False,
        exit_code=1,
        reason="stopped_budget",
        reservation_id=None,
        claim_id=None,
    )

    result = mp.call_claude("system", "user prompt")

    assert result == ""
    mock_finalize.assert_not_called()


@patch("mail_pipeline.mail_pipeline._push_metrics_line")
@patch("mail_pipeline.mail_pipeline._main_body")
@patch("mail_pipeline.mail_pipeline.get_unprocessed_count", return_value=42)
def test_main_logs_remaining_backlog(mock_get_unprocessed, mock_main_body, mock_push):
    with patch.object(mp, "log") as mock_log:
        mp.main()

    mock_get_unprocessed.assert_called_once()
    mock_log.assert_any_call("残りバックログ: 42件")


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "raw_inbox.db"
