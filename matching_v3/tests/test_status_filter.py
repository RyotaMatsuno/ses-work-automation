"""test_status_filter.py — 稼働状況フィルタリングのテスト (Phase 2A1)"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notion_client import NotionClient


class DummyConfig:
    notion_api_key = "secret"


def _mock_page(status: str | None) -> dict:
    """Notion APIが返すページ構造を模倣する。情報取得日=今日で鮮度OK。"""
    today = date.today().isoformat()
    return {
        "id": "eng-test-001",
        "last_edited_time": f"{today}T00:00:00.000Z",
        "properties": {
            "名前": {"title": [{"plain_text": "テストエンジニア"}]},
            "スキル": {"multi_select": [{"name": "Python"}]},
            "正規化スキル": {"multi_select": []},
            "単価": {"number": None},
            "単価（万円）": {"number": 60.0},
            "経験年数": {"number": 3},
            "稼働状況": {"select": {"name": status}} if status else {"select": None},
            "稼働可能日": {"date": None},
            "居住地": {"select": None},
            "担当者": {"select": None},
            "提案対象フラグ": {"checkbox": True},
            "備考（LINEメモ）": {"rich_text": []},
            "国籍": {"select": None},
            "年齢": {"number": None},
            "最終更新日": {"date": None},
            "情報取得日": {"date": {"start": today}},
        },
    }


def _client_with_status(status: str | None) -> NotionClient:
    session = Mock()
    res = Mock()
    res.status_code = 200
    res.json.return_value = {"results": [_mock_page(status)], "has_more": False}
    res.raise_for_status.return_value = None
    session.request.return_value = res
    return NotionClient(config=DummyConfig(), session=session)


def test_status_excluded() -> None:
    """稼働中エンジニアは Active Pool から除外される。"""
    result = _client_with_status("稼働中").get_active_engineers()
    assert result == []


def test_blank_status_included() -> None:
    """空欄（未設定）エンジニアは Active Pool に含まれる。"""
    result = _client_with_status(None).get_active_engineers()
    assert len(result) == 1


def test_available_included() -> None:
    """稼働可能エンジニアは Active Pool に含まれる。"""
    result = _client_with_status("稼働可能").get_active_engineers()
    assert len(result) == 1


def test_adjusting_included() -> None:
    """調整中エンジニアは Active Pool に含まれる。"""
    result = _client_with_status("調整中").get_active_engineers()
    assert len(result) == 1
