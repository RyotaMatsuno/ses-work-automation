from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from skill_extractor import (  # noqa: E402
    enrich_engineer_info,
    estimate_price_from_experience,
    extract_experience_years,
    extract_price_man_yen,
    extract_skills_from_plain_text,
)


VALID_SKILLS = ["Java", "Spring", "AWS", "Docker", "Python"]


def test_extract_price_and_experience():
    text = "28歳女性 Java5年 基本設計から対応 単価65万 即日稼働可"
    assert extract_price_man_yen(text) == 65
    assert extract_experience_years(text) == 5


def test_extract_skills_from_plain_text():
    text = "スキル: Java, Spring Boot, AWS, Docker"
    skills = extract_skills_from_plain_text(text, VALID_SKILLS + ["Spring Boot"])
    assert "Java" in skills
    assert "AWS" in skills


def test_enrich_engineer_info_sets_price_from_experience():
    info = enrich_engineer_info({}, "経験5年 製造中心", VALID_SKILLS)
    assert info["experience_years"] == 5
    assert info["price"] == estimate_price_from_experience(5)


def test_is_personnel_summary_detects_age_gender_line():
    from webhook_server import is_personnel_summary

    assert is_personnel_summary("28歳女性\nJava5年 基本設計から") is True
    assert is_personnel_summary("案件の件でご相談です") is False


def test_get_user_session_expires_after_ttl():
    from webhook_server import BUFFER_TTL, USER_BUFFER, get_user_session, start_user_session

    USER_BUFFER.clear()
    start_user_session("user-1", "28歳女性 Java", "page-1")
    assert get_user_session("user-1")["engineer_page_id"] == "page-1"

    USER_BUFFER["user-1"]["timestamp"] = time.time() - BUFFER_TTL - 1
    assert get_user_session("user-1") == {}


@patch("webhook_server.push_message")
@patch("webhook_server.reply_message")
@patch("webhook_server.run_reverse_matching_full", return_value={"matches": [], "stats": {}})
@patch("webhook_server.get_active_projects", return_value=[])
@patch("webhook_server._patch_engineer_page", return_value=(True, "page-1"))
@patch("skill_extractor.analyze_skill_sheet_v2")
@patch("webhook_server.requests.get")
def test_handle_file_message_uses_pending_session(
    mock_get, mock_analyze, mock_patch, _mock_projects, _mock_reverse, _mock_reply, _mock_push
):
    from webhook_server import USER_BUFFER, handle_file_message, start_user_session

    USER_BUFFER.clear()
    start_user_session("user-1", "28歳女性 Java5年", "page-1")

    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"excel-bytes"
    mock_analyze.return_value = {
        "name": "Y.S",
        "skills": [{"name": "Java", "years": 5, "active": True}],
        "price": 65,
        "experience_years": 5,
    }

    handle_file_message(
        "msg-1",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "token",
        "matsuno",
        "token",
        user_id="user-1",
    )

    mock_patch.assert_called_once()
    assert mock_patch.call_args[0][0] == "page-1"
    assert "user-1" not in USER_BUFFER
