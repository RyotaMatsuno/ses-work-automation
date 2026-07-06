from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from common.sheet_fetcher import extract_spreadsheet_id, fetch_sheet_text


def test_extract_spreadsheet_id():
    url = "https://docs.google.com/spreadsheets/d/abc123XYZ/edit#gid=0"
    assert extract_spreadsheet_id(url) == "abc123XYZ"


@patch("common.sheet_fetcher.fetch_sheet_text_playwright")
@patch("common.sheet_fetcher.fetch_sheet_text_via_oauth")
def test_fetch_sheet_text_prefers_oauth(mock_oauth, mock_playwright, tmp_path):
    token_path = tmp_path / "drive_token.json"
    token_path.write_text('{"access_token":"x","refresh_token":"y","client_id":"a","client_secret":"b"}', encoding="utf-8")
    mock_oauth.return_value = {"status": "ok", "text": "sheet-data", "url": "u"}
    result = fetch_sheet_text("https://docs.google.com/spreadsheets/d/abc/edit", oauth_token_path=token_path)
    assert result["status"] == "ok"
    mock_oauth.assert_called_once()
    mock_playwright.assert_not_called()
