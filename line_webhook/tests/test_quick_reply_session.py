from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_build_skill_sheet_format_quick_reply():
    from webhook_server import QUICK_REPLY_LABEL_FILE, QUICK_REPLY_LABEL_SHEET, build_skill_sheet_format_quick_reply

    payload = build_skill_sheet_format_quick_reply()
    assert "quickReply" in payload
    labels = [item["action"]["text"] for item in payload["quickReply"]["items"]]
    assert QUICK_REPLY_LABEL_FILE in labels
    assert QUICK_REPLY_LABEL_SHEET in labels


def test_extract_sheet_url_from_summary():
    from webhook_server import extract_sheet_url_from_text

    text = "28歳女性\nhttps://docs.google.com/spreadsheets/d/abc123XYZ/edit#gid=0"
    assert "abc123XYZ" in extract_sheet_url_from_text(text)


@patch("webhook_server.requests.post")
def test_reply_line_message_sends_quick_reply(mock_post):
    from webhook_server import build_skill_sheet_format_quick_reply, reply_line_message

    reply_line_message("token", build_skill_sheet_format_quick_reply(), "line-token")
    body = mock_post.call_args.kwargs["json"]
    message = body["messages"][0]
    assert message["quickReply"]["items"][0]["action"]["text"] == "ファイル送信"


@patch("webhook_server._process_skill_sheet_text")
@patch("webhook_server.fetch_sheet_text")
@patch("webhook_server.reply_message")
def test_quick_reply_sheet_fetches_and_processes(mock_reply, mock_fetch, mock_process):
    from webhook_server import (
        SESSION_STATE_PENDING,
        USER_BUFFER,
        handle_session_spreadsheet_choice,
        start_user_session,
    )

    USER_BUFFER.clear()
    summary = "28歳女性\nhttps://docs.google.com/spreadsheets/d/abc123/edit"
    start_user_session("user-1", summary, "page-1", state=SESSION_STATE_PENDING)
    mock_fetch.return_value = {"status": "ok", "text": "Java\tSpring\n" * 30}

    handle_session_spreadsheet_choice("user-1", USER_BUFFER["user-1"], "reply", "matsuno", "token")

    mock_fetch.assert_called_once()
    mock_process.assert_called_once()


@patch("webhook_server.push_message")
@patch("webhook_server.fetch_sheet_text")
@patch("webhook_server.reply_message")
def test_quick_reply_sheet_permission_error_falls_back_to_file(mock_reply, mock_fetch, mock_push):
    from webhook_server import (
        SESSION_STATE_PENDING,
        SESSION_STATE_WAITING_FILE,
        USER_BUFFER,
        handle_session_spreadsheet_choice,
        start_user_session,
    )

    USER_BUFFER.clear()
    summary = "28歳女性\nhttps://docs.google.com/spreadsheets/d/abc123/edit"
    start_user_session("user-1", summary, "page-1", state=SESSION_STATE_PENDING)
    mock_fetch.return_value = {"status": "login_required"}

    handle_session_spreadsheet_choice("user-1", USER_BUFFER["user-1"], "reply", "matsuno", "token")

    assert USER_BUFFER["user-1"]["state"] == SESSION_STATE_WAITING_FILE
    mock_push.assert_called_once()
    assert "Excel/Word" in mock_push.call_args[0][1]


@patch("webhook_server.reply_message")
def test_quick_reply_file_sets_waiting_state(mock_reply):
    from webhook_server import (
        QUICK_REPLY_LABEL_FILE,
        SESSION_STATE_PENDING,
        SESSION_STATE_WAITING_FILE,
        USER_BUFFER,
        get_user_session,
        start_user_session,
    )
    from webhook_server import process_message

    USER_BUFFER.clear()
    start_user_session("user-1", "28歳女性 Java", "page-1", state=SESSION_STATE_PENDING)

    with patch("webhook_server.handle_line_query", return_value=None):
        process_message(
            QUICK_REPLY_LABEL_FILE,
            "reply-token",
            "matsuno",
            "line-token",
            user_id="user-1",
        )

    assert get_user_session("user-1")["state"] == SESSION_STATE_WAITING_FILE
    mock_reply.assert_called()
