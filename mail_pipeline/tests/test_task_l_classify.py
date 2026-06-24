# -*- coding: utf-8 -*-
"""Task L: classification recall improvements."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from analyze_final import classify_by_rule, should_promote_other_to_project
from mail_pipeline import raw_inbox as ri


@pytest.mark.parametrize(
    "subject,expected",
    [
        ("【案件配信】7月〜/UiPath案件", "project"),
        ("【フルリモート/〜65万円/TypeScript】AI開発", "project"),
        ("決済者直【C/C++/常駐】", "project"),
        ("【8月開始】購買管理PL/SQL募集（4名）", "project"),
        ("★フルリモート!【Go / 80万〜90万】EC開発", "project"),
        ("【SES交流会】つながりが次の案件をつくる", "skip"),
        ("【イルミナ：要員】M.N（29歳）", "engineer"),
        ("【BTM案件】Go/基本リモート", "project"),
        ("お世話になっております", "unknown"),
    ],
)
def test_task_l_rule_classification(subject: str, expected: str) -> None:
    assert classify_by_rule(subject, "sales@example.com") == expected


def test_should_promote_other_to_project() -> None:
    assert should_promote_other_to_project("【案件配信】7月〜/UiPath案件") is True
    assert should_promote_other_to_project("お世話になっております") is False


def test_reset_other_for_reclassify(tmp_path: Path) -> None:
    db = tmp_path / "raw_inbox.db"
    ri.insert_raw_email(
        message_id="<other-project@x>",
        account="sessales",
        received_at="2026-06-19T10:00:00",
        sender="s@example.com",
        subject="【案件配信】7月〜/UiPath案件",
        body_text="body",
        db_path=db,
    )
    ri.mark_processed("<other-project@x>", classify_result="other", db_path=db)
    ri.insert_raw_email(
        message_id="<other-plain@x>",
        account="sessales",
        received_at="2026-06-19T10:00:00",
        sender="s@example.com",
        subject="お世話になっております",
        body_text="body",
        db_path=db,
    )
    ri.mark_processed("<other-plain@x>", classify_result="other", db_path=db)

    reset_count = ri.reset_other_for_reclassify(db)
    assert reset_count == 1
    assert ri.count_unprocessed(db) == 1


@patch("mail_pipeline.mail_pipeline._finalize_batch_usage")
@patch("mail_pipeline.mail_pipeline._batch_budget_reserve")
@patch("analyze_final.classify_by_rule", return_value="unknown")
def test_classify_email_v2_promotes_other_to_project(mock_rule, mock_reserve, mock_finalize_batch) -> None:
    import json
    from types import SimpleNamespace

    import mail_pipeline.mail_pipeline as mp

    mock_reserve.return_value = SimpleNamespace(
        allowed=True,
        exit_code=0,
        reservation_id="res-1",
        claim_id=None,
    )

    classify_line = json.dumps(
        {
            "custom_id": "classify_0",
            "result": {
                "type": "succeeded",
                "message": {
                    "content": [{"text": '{"type":"other"}'}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                    "model": "claude-haiku-4-5-20251001",
                },
            },
        },
        ensure_ascii=False,
    )
    extract_line = json.dumps(
        {
            "custom_id": "extract_project_0",
            "result": {
                "type": "succeeded",
                "message": {
                    "content": [{"text": '{"type":"project","name":"UiPath"}'}],
                    "usage": {"input_tokens": 20, "output_tokens": 10},
                    "model": "claude-haiku-4-5-20251001",
                },
            },
        },
        ensure_ascii=False,
    )

    with patch.object(mp, "ANTHROPIC_KEY", "test-key"):
        with patch("mail_pipeline.mail_pipeline.requests") as mock_requests:
            create_res = MagicMock()
            create_res.status_code = 200
            create_res.json.return_value = {"id": "batch-1"}
            status_res = MagicMock()
            status_res.status_code = 200
            status_res.json.return_value = {"processing_status": "ended"}
            results_res_classify = MagicMock()
            results_res_classify.status_code = 200
            results_res_classify.text = classify_line
            results_res_extract = MagicMock()
            results_res_extract.status_code = 200
            results_res_extract.text = extract_line
            mock_requests.post.return_value = create_res
            mock_requests.get.side_effect = [status_res, results_res_classify, status_res, results_res_extract]

            result = mp.classify_email_v2(
                [
                    {
                        "index": 0,
                        "subject": "【案件配信】7月〜/UiPath案件",
                        "sender": "a@b.com",
                        "body": "本文",
                    }
                ]
            )

    assert result[0]["type"] == "project"
