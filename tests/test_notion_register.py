from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common.notion_register import register_project

DB_ID = "test-db-id"
HEADERS = {"Authorization": "Bearer test", "Notion-Version": "2022-06-28"}
PROJECT_NAME = "Java案件"
SOURCE = "共通メール"


def _project_properties(name: str = PROJECT_NAME, source: str = SOURCE) -> dict:
    return {
        "案件名": {"title": [{"text": {"content": name}}]},
        "入力元": {"select": {"name": source}},
        "ステータス": {"select": {"name": "募集中"}},
    }


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = f"status {status_code}"
    resp.json.return_value = json_data or {}
    resp.ok = status_code < 400
    return resp


@patch("common.notion_register.requests.request")
def test_register_project_creates_when_not_found(mock_request: MagicMock) -> None:
    mock_request.side_effect = [
        _mock_response(200, {"results": []}),
        _mock_response(200, {"id": "new-page-id"}),
    ]

    result = register_project(
        _project_properties(),
        DB_ID,
        headers=HEADERS,
    )

    assert result["action"] == "create"
    assert result["page_id"] == "new-page-id"
    assert mock_request.call_count == 2
    assert mock_request.call_args_list[0].args[0] == "POST"
    assert "/databases/" in mock_request.call_args_list[0].args[1]
    assert mock_request.call_args_list[1].args[0] == "POST"
    assert mock_request.call_args_list[1].args[1] == "https://api.notion.com/v1/pages"


@patch("common.notion_register.requests.request")
def test_register_project_updates_when_found(mock_request: MagicMock) -> None:
    mock_request.side_effect = [
        _mock_response(200, {"results": [{"id": "existing-page-id"}]}),
        _mock_response(200, {}),
    ]

    result = register_project(
        _project_properties(),
        DB_ID,
        headers=HEADERS,
    )

    assert result["action"] == "update"
    assert result["page_id"] == "existing-page-id"
    assert mock_request.call_count == 2
    assert mock_request.call_args_list[0].args[0] == "POST"
    assert "/databases/" in mock_request.call_args_list[0].args[1]
    assert mock_request.call_args_list[1].args[0] == "PATCH"
    assert mock_request.call_args_list[1].args[1].endswith("/pages/existing-page-id")


@patch("common.notion_register.requests.request")
def test_register_project_force_create_posts_even_when_found(mock_request: MagicMock) -> None:
    mock_request.return_value = _mock_response(200, {"id": "forced-page-id"})

    result = register_project(
        _project_properties(),
        DB_ID,
        headers=HEADERS,
        force_create=True,
    )

    assert result["action"] == "create"
    assert result["page_id"] == "forced-page-id"
    mock_request.assert_called_once()
    assert mock_request.call_args.args[0] == "POST"
    assert mock_request.call_args.args[1] == "https://api.notion.com/v1/pages"
