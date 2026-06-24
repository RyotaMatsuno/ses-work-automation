"""Task AE: push_fail キュー投入防止テスト."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from nightly_jobz.notion_queue import QueueTask, fetch_queued_tasks, is_rejected_enqueue


@pytest.fixture
def push_error_log(tmp_path, monkeypatch):
    log_path = tmp_path / "push_errors.log"
    monkeypatch.setattr("line_webhook.line_bridge._PUSH_ERROR_LOG", log_path)
    return log_path


def test_is_rejected_enqueue_blocks_push_fail_dev():
    assert is_rejected_enqueue("dev", "push_fail_20260623120000") is True
    assert is_rejected_enqueue("dev", "normal_task") is False
    assert is_rejected_enqueue("investigation", "push_fail_x") is False


@patch("nightly_jobz.notion_queue._request")
def test_fetch_queued_tasks_filters_push_fail(mock_request):
    mock_request.return_value = {
        "results": [
            {
                "id": "p1",
                "properties": {
                    "task_id": {"title": [{"plain_text": "push_fail_20260623120000"}]},
                    "種別": {"select": {"name": "dev"}},
                    "状態": {"select": {"name": "queued"}},
                    "入力データ": {"rich_text": []},
                },
            },
            {
                "id": "p2",
                "properties": {
                    "task_id": {"title": [{"plain_text": "T-normal"}]},
                    "種別": {"select": {"name": "investigation"}},
                    "状態": {"select": {"name": "queued"}},
                    "入力データ": {"rich_text": []},
                },
            },
        ]
    }

    tasks = fetch_queued_tasks(limit=10)

    assert len(tasks) == 1
    assert tasks[0].task_id == "T-normal"


@patch("line_webhook.line_bridge._notion_request")
@patch("line_webhook.line_bridge._send_line_push_raw", return_value=False)
@patch("line_webhook.line_bridge._line_push_remaining", return_value=180)
def test_push_failure_logs_to_file_not_queue(mock_remaining, mock_push, mock_notion, push_error_log):
    from line_webhook.line_bridge import push_or_log

    result = push_or_log("Utest", "push failed message", task_id="")

    assert result == "error_logged"
    mock_push.assert_called_once()
    mock_notion.assert_not_called()
    entry = json.loads(push_error_log.read_text(encoding="utf-8").strip())
    assert entry["reason"] == "LINE push失敗"
    assert entry["text"] == "push failed message"


@patch("line_webhook.line_bridge._update_page")
@patch("line_webhook.line_bridge._find_task")
@patch("line_webhook.line_bridge._notion_request")
@patch("line_webhook.line_bridge._send_line_push_raw", return_value=False)
@patch("line_webhook.line_bridge._line_push_remaining", return_value=180)
def test_push_failure_updates_existing_task_only(
    mock_remaining,
    mock_push,
    mock_notion,
    mock_find_task,
    mock_update_page,
    push_error_log,
):
    from line_webhook.line_bridge import push_or_log

    mock_find_task.return_value = {
        "id": "page-1",
        "properties": {"結果リンク": {"rich_text": [{"plain_text": "既存"}]}},
    }

    result = push_or_log("Utest", "retry notice", task_id="mail_pipeline_run")

    assert result == "notion_logged"
    mock_update_page.assert_called_once()
    post_calls = [call for call in mock_notion.call_args_list if call.args and call.args[0] == "POST"]
    assert not any(call.args[1] == "pages" for call in post_calls)
    entry = json.loads(push_error_log.read_text(encoding="utf-8").strip())
    assert entry["task_id"] == "mail_pipeline_run"
