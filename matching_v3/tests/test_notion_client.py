from __future__ import annotations

from unittest.mock import Mock, patch

from notion_client import NotionClient


class DummyConfig:
    notion_api_key = "secret"


def _response(status_code: int, payload: dict):
    res = Mock()
    res.status_code = status_code
    res.text = "body"
    res.json.return_value = payload
    res.raise_for_status.return_value = None
    return res


def test_get_new_cases_builds_filter():
    session = Mock()
    session.request.return_value = _response(200, {"results": [], "has_more": False})
    client = NotionClient(config=DummyConfig(), session=session)

    client.get_new_cases(days=4)

    payload = session.request.call_args.kwargs["json"]
    assert payload["filter"]["and"][0]["timestamp"] == "created_time"
    assert "on_or_after" in payload["filter"]["and"][0]["created_time"]


def test_request_retries_two_500_then_success():
    session = Mock()
    session.request.side_effect = [
        _response(500, {}),
        _response(500, {}),
        _response(200, {"results": [], "has_more": False}),
    ]
    client = NotionClient(config=DummyConfig(), session=session)

    with patch("notion_client.time.sleep"):
        client.get_new_cases(days=4)

    assert session.request.call_count == 3
