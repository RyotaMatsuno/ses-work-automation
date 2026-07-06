from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import requests
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


def test_get_active_engineers_failopen_on_400_filter_error(caplog):
    """400 filter error → fail-open (fallback to no-filter) + WARNING logged.
    _request retries 3 times before raising, so we need 3 filter responses + 1 fallback.
    """
    import logging

    exc_400 = requests.HTTPError("bad request")
    exc_400.response = Mock()
    exc_400.response.status_code = 400

    def make_filter_resp():
        r = Mock()
        r.status_code = 400
        r.text = "bad request"
        r.raise_for_status.side_effect = exc_400
        return r

    fallback_response = Mock()
    fallback_response.status_code = 200
    fallback_response.raise_for_status.return_value = None
    fallback_response.json.return_value = {"results": [], "has_more": False}

    session = Mock()
    session.request.side_effect = [
        make_filter_resp(),
        make_filter_resp(),
        make_filter_resp(),
        fallback_response,
    ]
    client = NotionClient(config=DummyConfig(), session=session)

    with patch("notion_client.time.sleep"):
        with caplog.at_level(logging.WARNING, logger="notion_client"):
            result = client.get_active_engineers()

    assert isinstance(result, list)
    assert any("フィルタ" in msg or "スキップ" in msg for msg in caplog.messages)
