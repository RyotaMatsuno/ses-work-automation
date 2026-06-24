"""Task H: push_or_log quota / reply-only / push 境界テスト."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest


@pytest.fixture
def push_skip_log(tmp_path, monkeypatch):
    log_path = tmp_path / "line_push_skipped.jsonl"
    monkeypatch.setattr("line_webhook.line_bridge._PUSH_SKIP_LOG", log_path)
    return log_path


@pytest.fixture
def push_error_log(tmp_path, monkeypatch):
    log_path = tmp_path / "push_errors.log"
    monkeypatch.setattr("line_webhook.line_bridge._PUSH_ERROR_LOG", log_path)
    return log_path


def _notion_ok(*_args, **_kwargs):
    return {"results": []}


@patch("line_webhook.line_bridge._notion_request", side_effect=_notion_ok)
@patch("line_webhook.line_bridge._send_line_push_raw", return_value=True)
@patch("line_webhook.line_bridge._line_push_remaining", return_value=180)
def test_push_when_remaining_above_threshold(mock_remaining, mock_push, _mock_notion, push_skip_log):
    from line_webhook.line_bridge import push_or_log

    result = push_or_log("Utest", "hello", task_id="")

    assert result == "pushed"
    mock_push.assert_called_once_with("Utest", "hello")
    assert not push_skip_log.exists()


@patch("line_webhook.line_bridge._notion_request", side_effect=_notion_ok)
@patch("line_webhook.line_bridge._send_line_push_raw", return_value=True)
@patch("line_webhook.line_bridge._line_push_remaining", return_value=-1)
def test_skip_push_when_quota_fetch_failed(mock_remaining, mock_push, _mock_notion, push_skip_log, push_error_log):
    from line_webhook.line_bridge import push_or_log

    result = push_or_log("Utest", "quota fail msg", task_id="")

    mock_push.assert_not_called()
    assert result == "error_logged"
    lines = push_skip_log.read_text(encoding="utf-8").strip().split("\n")
    entry = json.loads(lines[0])
    assert entry["reason"] == "LINE quota取得失敗"
    assert "quota fail msg" in entry["text"]
    error_entry = json.loads(push_error_log.read_text(encoding="utf-8").strip())
    assert error_entry["reason"] == "LINE quota取得失敗"
    _mock_notion.assert_not_called()


@patch("line_webhook.line_bridge._notion_request", side_effect=_notion_ok)
@patch("line_webhook.line_bridge._send_line_push_raw", return_value=True)
@patch("line_webhook.line_bridge._line_push_remaining", return_value=100)
def test_reply_only_when_remaining_below_threshold(mock_remaining, mock_push, _mock_notion, push_skip_log, push_error_log):
    from line_webhook.line_bridge import push_or_log

    result = push_or_log("Utest", "reply only msg", task_id="")

    mock_push.assert_not_called()
    assert result == "error_logged"
    entry = json.loads(push_skip_log.read_text(encoding="utf-8").strip())
    assert "reply-only" in entry["reason"]
    assert entry["text"] == "reply only msg"
    _mock_notion.assert_not_called()


@patch("line_webhook.line_bridge._notion_request", side_effect=_notion_ok)
@patch("line_webhook.line_bridge._send_line_push_raw", return_value=True)
@patch("line_webhook.line_bridge._line_push_remaining", return_value=0)
def test_skip_push_when_remaining_zero(mock_remaining, mock_push, _mock_notion, push_skip_log, push_error_log):
    from line_webhook.line_bridge import push_or_log

    result = push_or_log("Utest", "zero remaining", task_id="")

    mock_push.assert_not_called()
    assert result == "error_logged"
    _mock_notion.assert_not_called()
