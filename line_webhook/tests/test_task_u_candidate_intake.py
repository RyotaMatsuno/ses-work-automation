# -*- coding: utf-8 -*-
"""Task U: LINE candidate intake routing tests."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from line_bridge import (  # noqa: E402
    _parse_candidate_text,
    classify_route,
    route_line_message,
)


SAMPLE_URL = "https://docs.google.com/spreadsheets/d/abc123/edit#gid=0"
SAMPLE_BODY = (
    f"{SAMPLE_URL}\n"
    "【名前】Y.S（33歳男性）\n"
    "【最寄】船橋競馬場駅\n"
    "【単価】40万\n"
    "【スキル】Java, AWS, Docker"
)


def test_classify_route_sheet_url_with_candidate_format():
    route = classify_route(SAMPLE_BODY)
    assert route["route"] == "candidate_intake"
    assert route["kind"] == "engineer_registration"
    assert route["assignee"] == "jobz"


def test_classify_route_candidate_format_beats_development_keywords():
    text = "【名前】T.K\nバグ修正して\n実装して"
    route = classify_route(text)
    assert route["route"] == "candidate_intake"


def test_classify_route_ph_matching_unchanged():
    route = classify_route("PH 京成小岩")
    assert route["route"] == "immediate"
    assert route["kind"] == "matching"


def test_classify_route_development_unchanged():
    route = classify_route("バグ修正して")
    assert route["route"] == "development"
    assert route["kind"] == "dev"


def test_parse_candidate_text_structured_fields():
    text = (
        "【名前】Y.S（33歳男性）\n"
        "【最寄】船橋競馬場駅\n"
        "【単価】40万\n"
        "【スキル】Java, AWS"
    )
    parsed = _parse_candidate_text(text)
    assert parsed is not None
    assert parsed["name"] == "Y.S（33歳男性）"
    assert parsed["station"] == "船橋競馬場駅"
    assert parsed["price"] == "40"
    assert parsed["skills"] == ["Java", "AWS"]
    assert parsed["age_gender"] == "33歳男性"


def test_parse_candidate_text_extracts_sheet_url():
    parsed = _parse_candidate_text(SAMPLE_BODY)
    assert parsed is not None
    assert parsed["sheet_url"] == SAMPLE_URL


def test_parse_candidate_text_requires_name():
    assert _parse_candidate_text("【単価】40万\n【最寄】船橋") is None


@patch("line_bridge._check_duplicate_engineer", return_value=True)
@patch("line_bridge.enqueue_task")
def test_route_line_message_duplicate_blocked(mock_enqueue, _mock_dup):
    result = route_line_message(
        SAMPLE_BODY,
        user_id="Ue3508b43b84991f5a68281da5bf4cf39",
        message_id="msg-dup",
        event_timestamp_ms=1_700_000_000_000,
        reply_token="token",
    )
    assert result["action"] == "reply"
    assert "既に登録済み" in result["text"]
    mock_enqueue.assert_not_called()


@patch("line_bridge._check_duplicate_engineer", return_value=False)
@patch("line_bridge.enqueue_task", return_value=(True, "task-u-1"))
def test_route_line_message_enqueues_candidate(mock_enqueue, _mock_dup):
    result = route_line_message(
        SAMPLE_BODY,
        user_id="Ue3508b43b84991f5a68281da5bf4cf39",
        message_id="msg-new",
        event_timestamp_ms=1_700_000_000_000,
        reply_token="token",
    )
    assert result["action"] == "reply"
    assert "候補者を検出しました" in result["text"]
    assert "Y.S" in result["text"]
    mock_enqueue.assert_called_once()
    route = mock_enqueue.call_args[0][1]
    assert route["route"] == "candidate_intake"
    assert route["kind"] == "engineer_registration"
