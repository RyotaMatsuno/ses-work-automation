from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "matching_v3"))

from staleness_checker import check

from mail_pipeline import mail_pipeline as mp
from mail_pipeline.validation import ValidationResult, append_remark, normalize_price_yen, price_field_unit


def test_get_active_engineers_includes_null_info_acquired_date():
    pages = [
        {
            "id": "no-date",
            "last_edited_time": "2026-05-21T12:00:00+00:00",
            "properties": {
                "名前": {"title": [{"plain_text": "フォールバック太郎"}]},
                "スキル": {"multi_select": []},
                "単価（万円）": {"number": 60},
                "提案対象フラグ": {"checkbox": True},
                "備考（LINEメモ）": {"rich_text": []},
            },
        }
    ]
    notion = Mock()
    notion.get_active_engineers.return_value = [
        {
            "id": "no-date",
            "名前": "フォールバック太郎",
            "情報取得日": None,
            "_last_edited_time": "2026-05-21T12:00:00+00:00",
            "単価（万円）": 60,
            "提案対象フラグ": True,
            "備考（LINEメモ）": "",
        }
    ]

    engineers = notion.get_active_engineers()
    result = check(engineers[0], today=__import__("datetime").date(2026, 6, 10))

    assert result["source_field"] == "last_edited_time"
    assert result["is_fresh"] is True


def test_normalize_price_from_man_yen_field():
    assert normalize_price_yen(50) == 500_000


def test_price_field_unit_for_yen_and_man():
    assert price_field_unit("単価") == "yen"
    assert price_field_unit("単価（万円）") == "man"


def test_append_remark_skips_when_existing_too_long():
    base = "a" * 1900
    merged = append_remark(base, ["[validation] 追記"])
    assert merged == base


def test_internaldate_utc_to_jst_next_day():
    parsed = mp._parse_imap_internaldate(b'1 (INTERNALDATE "10-Jun-2026 15:30:00 +0000")')
    assert parsed is not None
    assert parsed.date().isoformat() == "2026-06-11"


@patch("mail_pipeline.mail_pipeline.save_processed_id")
@patch("mail_pipeline.mail_pipeline.notion_register_engineer")
def test_notion_register_failure_does_not_save_processed_id(mock_register, mock_save):
    mock_register.side_effect = mp.NotionAPIError(500, "server error")
    mp.ENGINEER_PROP_NAMES = {
        "氏名": "名前",
        "備考": "備考（LINEメモ）",
        "スキル": "スキル",
        "単価": "単価（万円）",
        "稼働開始日": "稼働可能日",
        "提案対象フラグ": "提案対象フラグ",
        "情報取得日": "情報取得日",
    }

    ok, _ = mp.register_engineer(
        {"name": "山田太郎", "skills": ["Java"], "price": 60, "available_date": "2026-07-01"},
        "件名",
        "sender@example.com",
        validation=ValidationResult(status="OK", proposal_target=True),
        received_at=datetime.now(timezone.utc),
    )

    assert ok is False
    mock_save.assert_not_called()


@patch("mail_pipeline.mail_pipeline.save_processed_id")
def test_validation_skip_saves_processed_id(mock_save):
    processed = set()
    mp.maybe_save_processed_id("msg-1", processed, dry_run=False)
    mock_save.assert_called_once_with("msg-1", processed)


def test_processed_ids_file_roundtrip(tmp_path, monkeypatch):
    path = tmp_path / "processed_ids.json"
    monkeypatch.setattr(mp, "PROCESSED_IDS_PATH", path)

    processed = mp.load_processed_ids()
    mp.save_processed_id("abc", processed)

    reloaded = mp.load_processed_ids()
    assert "abc" in reloaded


@patch("mail_pipeline.mail_pipeline.save_processed_id")
@patch("mail_pipeline.mail_pipeline.increment_retry_count", return_value=1)
def test_finalize_processed_state_keeps_unprocessed_on_notion_failure(mock_retry, mock_save):
    processed = set()
    mp.finalize_processed_state(
        "msg-fail",
        processed,
        "project",
        notion_register_failed=True,
        subject="失敗案件",
    )
    mock_retry.assert_called_once()
    mock_save.assert_not_called()


@patch("mail_pipeline.mail_pipeline._notify_notion_retry_give_up")
@patch("mail_pipeline.mail_pipeline.save_processed_id")
@patch("mail_pipeline.mail_pipeline.increment_retry_count", return_value=3)
def test_finalize_processed_state_gives_up_after_three_retries(mock_retry, mock_save, mock_notify):
    processed = set()
    mp.finalize_processed_state(
        "msg-give-up",
        processed,
        "project",
        notion_register_failed=True,
        subject="上限案件",
    )
    mock_save.assert_called_once_with("msg-give-up", processed, classify_result="project")
    mock_notify.assert_called_once_with("msg-give-up", "上限案件", 3)


@patch("mail_pipeline.mail_pipeline.save_processed_id")
def test_finalize_processed_state_saves_on_success(mock_save):
    processed = set()
    mp.finalize_processed_state(
        "msg-ok",
        processed,
        "project",
        notion_register_failed=False,
    )
    mock_save.assert_called_once_with("msg-ok", processed, classify_result="project")


@patch("mail_pipeline.mail_pipeline.notion_register_project")
def test_register_project_delegates_to_common(mock_register):
    mock_register.return_value = {"ok": True, "page_id": "page-123"}
    ok, page_id = mp.register_project(
        {"name": "Java案件", "required_skills": [], "optional_skills": []},
        "件名",
        "sender@example.com",
    )
    assert ok is True
    assert page_id == "page-123"
    mock_register.assert_called_once()
