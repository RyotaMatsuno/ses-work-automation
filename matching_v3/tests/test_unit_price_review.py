from __future__ import annotations

import logging
from datetime import date
from unittest.mock import Mock, patch

from matcher import (
    MEMO_APPEND_MAX_LEN,
    build_unit_price_review_memo,
    exclude_unit_price_review_targets,
    find_unit_price_review_targets,
    review_invalid_unit_price,
    run_audit_unit_price,
    unit_price_review_reason,
)
from notion_client import NotionClient


class DummyConfig:
    notion_api_key = "secret"


def _response(status_code: int, payload: dict | None = None, text: str = ""):
    res = Mock()
    res.status_code = status_code
    res.text = text or "body"
    res.json.return_value = payload or {}
    res.raise_for_status.side_effect = None
    if status_code >= 400:
        import requests

        res.raise_for_status.side_effect = requests.HTTPError(response=res)
    return res


def test_unit_price_reason_null():
    assert unit_price_review_reason(None) == "単価未設定"


def test_unit_price_reason_empty_string():
    assert unit_price_review_reason("") == "単価未設定"
    assert unit_price_review_reason("   ") == "単価未設定"


def test_unit_price_reason_zero():
    assert unit_price_review_reason(0) == "単価0円"
    assert unit_price_review_reason(0.0) == "単価0円"


def test_unit_price_reason_negative():
    assert unit_price_review_reason(-1) == "単価が負数"
    assert unit_price_review_reason(-0.5) == "単価が負数"


def test_valid_unit_price_is_not_review_target():
    engineers = [
        {
            "id": "ok",
            "名前": "正常太郎",
            "提案対象フラグ": True,
            "単価（万円）": 60,
            "備考（LINEメモ）": "",
        }
    ]
    assert find_unit_price_review_targets(engineers) == []


def test_proposal_flag_false_is_skipped_even_with_invalid_price():
    engineers = [
        {
            "id": "skip",
            "名前": "対象外太郎",
            "提案対象フラグ": False,
            "単価（万円）": None,
            "備考（LINEメモ）": "",
        }
    ]
    assert find_unit_price_review_targets(engineers) == []


def test_build_memo_skips_duplicate_review_tag():
    existing = "メモあり\n【単価REVIEW】単価未設定 2026-06-01"
    assert build_unit_price_review_memo(existing, "単価0円", review_date=date(2026, 6, 10)) == existing


def test_review_invalid_unit_price_dry_run_does_not_update(caplog):
    engineers = [
        {
            "id": "bad",
            "名前": "未設定太郎",
            "提案対象フラグ": True,
            "単価（万円）": None,
            "備考（LINEメモ）": "",
        }
    ]
    updater = Mock()

    with caplog.at_level(logging.INFO):
        summary = review_invalid_unit_price(engineers, dry_run=True, updater=updater)

    assert summary["target_count"] == 1
    assert summary["update_success"] == 0
    assert summary["update_failed"] == 0
    updater.update_engineer_unit_price_review.assert_not_called()
    assert "[REVIEW] 未設定太郎 — 理由: 単価未設定" in caplog.text
    assert "REVIEW対象1件 / 更新成功0件 / 更新失敗0件" in caplog.text


def test_review_invalid_unit_price_exec_updates_notion():
    engineers = [
        {
            "id": "bad",
            "名前": "ゼロ太郎",
            "提案対象フラグ": True,
            "単価（万円）": 0,
            "備考（LINEメモ）": "既存メモ",
        }
    ]
    updater = Mock()
    updater.update_engineer_unit_price_review.return_value = True

    summary = review_invalid_unit_price(
        engineers,
        dry_run=False,
        updater=updater,
        review_date=date(2026, 6, 10),
    )

    assert summary["update_success"] == 1
    updater.update_engineer_unit_price_review.assert_called_once_with(
        "bad",
        "既存メモ\n【単価REVIEW】単価0円 2026-06-10",
    )


def test_exclude_unit_price_review_targets_removes_invalid_engineers():
    engineers = [
        {"id": "ok", "名前": "正常", "提案対象フラグ": True, "単価（万円）": 55},
        {"id": "bad", "名前": "負数", "提案対象フラグ": True, "単価（万円）": -3},
    ]
    result = exclude_unit_price_review_targets(engineers)
    assert [item["id"] for item in result] == ["ok"]


def test_notion_update_retries_429_then_succeeds():
    session = Mock()
    session.request.side_effect = [
        _response(429, text="rate limited"),
        _response(200, {"id": "page-1"}),
    ]
    client = NotionClient(config=DummyConfig(), session=session)

    with patch("notion_client.time.sleep"):
        ok = client.update_engineer_unit_price_review("page-1", "memo")

    assert ok is True
    assert session.request.call_count == 2


def test_get_proposal_target_engineers_paginates_over_100():
    session = Mock()
    first_page = {
        "results": [{"id": f"page-{i}", "properties": {}, "last_edited_time": "2026-06-01"} for i in range(100)],
        "has_more": True,
        "next_cursor": "cursor-2",
    }
    second_page = {
        "results": [{"id": "page-100", "properties": {}, "last_edited_time": "2026-06-01"}],
        "has_more": False,
        "next_cursor": None,
    }
    session.request.side_effect = [
        _response(200, first_page),
        _response(200, second_page),
    ]
    client = NotionClient(config=DummyConfig(), session=session)

    pages = client._query_database("db-id", {"filter": {"property": "提案対象フラグ", "checkbox": {"equals": True}}})

    assert len(pages) == 101
    assert session.request.call_count == 2


def test_review_invalid_unit_price_skips_long_memo(caplog):
    engineers = [
        {
            "id": "long-memo",
            "名前": "長文太郎",
            "提案対象フラグ": True,
            "単価（万円）": None,
            "備考（LINEメモ）": "x" * (MEMO_APPEND_MAX_LEN + 1),
        }
    ]
    updater = Mock()

    with caplog.at_level(logging.WARNING):
        summary = review_invalid_unit_price(engineers, dry_run=False, updater=updater)

    assert summary["update_failed"] == 1
    updater.update_engineer_unit_price_review.assert_not_called()
    assert "備考が長すぎるため追記スキップ" in caplog.text


def test_run_audit_unit_price_exec_returns_1_on_update_failure():
    engineers = [
        {
            "id": "bad",
            "名前": "失敗太郎",
            "提案対象フラグ": True,
            "単価（万円）": 0,
            "備考（LINEメモ）": "",
        }
    ]
    notion = Mock()
    notion.get_proposal_target_engineers.return_value = engineers
    notion.update_engineer_unit_price_review.return_value = False

    with patch("notion_client.NotionClient", return_value=notion):
        exit_code = run_audit_unit_price(exec_mode=True)

    assert exit_code == 1


def test_exclude_unit_price_review_targets_keeps_invalid_out_of_matching_pool():
    engineers = [
        {"id": "ok", "名前": "正常", "提案対象フラグ": True, "単価（万円）": 60},
        {"id": "bad", "名前": "未設定", "提案対象フラグ": True, "単価（万円）": None},
    ]
    result = exclude_unit_price_review_targets(engineers)
    assert {item["id"] for item in result} == {"ok"}
    assert all(unit_price_review_reason(item.get("単価（万円）")) is None for item in result)


def test_notion_update_400_logs_and_returns_false(caplog):
    session = Mock()
    session.request.return_value = _response(400, text="bad request")
    client = NotionClient(config=DummyConfig(), session=session)

    with caplog.at_level(logging.WARNING):
        ok = client.update_engineer_unit_price_review("page-1", "memo")

    assert ok is False
    assert session.request.call_count == 1
    assert "Notion 400 page_id=page-1" in caplog.text
