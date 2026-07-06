from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from line_bridge import MATSUNO_USER_ID, classify_route, route_line_message


def test_classify_route_unclassified_returns_pass():
    route = classify_route("28歳女性 Java5年 基本設計から")
    assert route["route"] == "pass"


def test_route_line_message_passes_through_for_personnel_summary():
    result = route_line_message(
        "28歳女性 Java5年",
        user_id=MATSUNO_USER_ID,
        message_id="msg-pass",
        event_timestamp_ms=1_700_000_000_000,
        reply_token="token",
    )
    assert result["action"] == "pass"
    assert "種別を1つ選んで" not in result.get("text", "")


def test_route_line_message_progress_command_still_works_via_handler():
    from line_bridge import handle_router_message

    result = handle_router_message(
        "進捗",
        user_id=MATSUNO_USER_ID,
        message_id="msg-progress",
        event_timestamp_ms=1_700_000_000_000,
    )
    assert result["handled"] is True
    assert "進捗コマンド" in result["reply"]
