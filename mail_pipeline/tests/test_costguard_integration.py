# -*- coding: utf-8 -*-
"""CostGuard v2 integration tests for mail_pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from mail_pipeline import mail_pipeline as mp


def test_get_today_cost_usd_removed():
    assert not hasattr(mp, "get_today_cost_usd")


def test_daily_cost_limit_constant_removed():
    assert not hasattr(mp, "DAILY_COST_LIMIT_USD")


@patch("mail_pipeline.mail_pipeline.finalize")
@patch("mail_pipeline.mail_pipeline.requests.post")
@patch("mail_pipeline.mail_pipeline.allowed")
def test_call_claude_returns_empty_when_costguard_blocks(mock_allowed, mock_post, mock_finalize):
    mock_allowed.return_value = SimpleNamespace(
        allowed=False,
        exit_code=1,
        reason="stopped_budget",
        reservation_id=None,
        claim_id=None,
    )

    result = mp.call_claude("system", "user prompt")

    assert result == ""
    mock_post.assert_not_called()
    mock_finalize.assert_not_called()


@patch("mail_pipeline.mail_pipeline.finalize")
def test_finalize_batch_usage_calls_finalize(mock_finalize):
    decision = SimpleNamespace(allowed=True, reservation_id="res-1", claim_id=None)
    items = [
        {
            "result": {
                "type": "succeeded",
                "message": {
                    "model": "claude-haiku-4-5-20251001",
                    "usage": {"input_tokens": 100, "output_tokens": 50},
                },
            }
        },
        {
            "result": {
                "type": "succeeded",
                "message": {
                    "model": "claude-haiku-4-5-20251001",
                    "usage": {"input_tokens": 30, "output_tokens": 20},
                },
            }
        },
    ]
    mp._finalize_batch_usage(decision, items, phase="classify")
    mock_finalize.assert_called_once_with(decision, in_tokens=130, out_tokens=70, success=True)


@patch("mail_pipeline.mail_pipeline._finalize_batch_usage")
@patch("mail_pipeline.mail_pipeline._batch_budget_reserve")
@patch("analyze_final.classify_by_rule", return_value="other")
def test_classify_email_v2_records_batch_usage(mock_rule, mock_reserve, mock_finalize_batch):
    mock_reserve.return_value = SimpleNamespace(
        allowed=True,
        exit_code=0,
        reservation_id="res-1",
        claim_id=None,
    )
    batch_result = [
        {
            "custom_id": "classify_0",
            "result": {
                "type": "succeeded",
                "message": {
                    "content": [{"text": '{"type":"skip"}'}],
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                    "model": "claude-haiku-4-5-20251001",
                },
            },
        }
    ]

    with patch.object(mp, "ANTHROPIC_KEY", "test-key"):
        with patch("mail_pipeline.mail_pipeline.requests") as mock_requests:
            create_res = MagicMock()
            create_res.status_code = 200
            create_res.json.return_value = {"id": "batch-1"}
            status_res = MagicMock()
            status_res.status_code = 200
            status_res.json.return_value = {"processing_status": "ended"}
            results_res = MagicMock()
            results_res.status_code = 200
            results_res.text = __import__("json").dumps(batch_result[0])
            mock_requests.post.return_value = create_res
            mock_requests.get.side_effect = [status_res, results_res]

            mp.classify_email_v2(
                [
                    {
                        "index": 0,
                        "subject": "テスト",
                        "sender": "a@b.com",
                        "body": "本文",
                    }
                ]
            )

    mock_finalize_batch.assert_called()
