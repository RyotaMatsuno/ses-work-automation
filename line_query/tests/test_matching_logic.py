"""
Test 1 & 2: line_query matching logic unit tests
line_webhook/line_query.py (メインバージョン) をテスト対象とする
PHさん(37万, #skill_skip)でマッチ>0件を確認するモックテスト
"""
import sys
import os
from unittest.mock import patch
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# line_webhook/line_query.py をインポート（メインバージョン）
_WEBHOOK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "line_webhook"))
sys.path.insert(0, _WEBHOOK_DIR)

import line_query as lq
from line_query import engineer_query, project_query, format_project_result, format_engineer_result


def _iso_now():
    return datetime.now(timezone.utc).isoformat()


def _make_engineer(name="PH", station="京成小岩", rate=37, skills=["PMO", "PHP"], note="#skill_skip", workst="稼働可能"):
    return {
        "id": "eng-001",
        "created_time": _iso_now(),
        "last_edited_time": _iso_now(),
        "properties": {
            lq.PROP_INI: {"type": "rich_text", "rich_text": [{"plain_text": name}]},
            lq.PROP_NAME: {"type": "title", "title": [{"plain_text": name}]},
            lq.PROP_STA: {"type": "rich_text", "rich_text": [{"plain_text": station}]},
            lq.PROP_SKILL: {"type": "multi_select", "multi_select": [{"name": s} for s in skills]},
            lq.PROP_RATE: {"type": "number", "number": rate},
            lq.PROP_STATUS: {"type": "select", "select": {"name": "募集中"}},
            lq.PROP_WORKST: {"type": "select", "select": {"name": workst}},
            lq.PROP_MEMO: {"type": "rich_text", "rich_text": [{"plain_text": note}]},
            lq.PROP_INPUT_SRC: {"type": "select", "select": None},
            lq.PROP_AFFIL: {"type": "rich_text", "rich_text": []},
            lq.PROP_AFFIL_CONT: {"type": "rich_text", "rich_text": []},
            lq.PROP_AFFIL_MAIL: {"type": "email", "email": None},
        },
    }


def _make_project(name="テスト案件A", rate=70, req_skills=[], status="募集中"):
    return {
        "id": "proj-001",
        "created_time": _iso_now(),
        "last_edited_time": _iso_now(),
        "properties": {
            lq.PROP_PJNAME: {"type": "title", "title": [{"plain_text": name}]},
            lq.PROP_REQSK: {"type": "multi_select", "multi_select": [{"name": s} for s in req_skills]},
            lq.PROP_OPTSK: {"type": "multi_select", "multi_select": []},
            lq.PROP_RATE: {"type": "number", "number": rate},
            lq.PROP_STATUS: {"type": "select", "select": {"name": status}},
            lq.PROP_ASSIGNEE: {"type": "select", "select": None},
            lq.PROP_REMOTE: {"type": "select", "select": None},
            lq.PROP_LOCATION: {"type": "rich_text", "rich_text": [{"plain_text": "東京"}]},
            lq.PROP_PERIOD: {"type": "rich_text", "rich_text": []},
            lq.PROP_PJDETAIL: {"type": "rich_text", "rich_text": []},
            lq.PROP_INPUT_SRC: {"type": "select", "select": None},
            # 情報取得日プロパティ (空 = created_time を使う)
            bytes.fromhex("e68385e5a0b1e58f96e5be97e697a5").decode(): {"type": "date", "date": None},
        },
    }


def test_skill_skip_engineer_matches_gross33_project():
    """PHさん(37万,#skill_skip)でgross=33の案件がマッチすること"""
    engineer = _make_engineer(rate=37, note="#skill_skip")
    project = _make_project(rate=70, req_skills=["Java"], status="募集中")

    with patch.object(lq, 'fetch_all_pages') as mock_fetch:
        mock_fetch.side_effect = [
            [engineer],  # engineers fetch
            [project],   # projects fetch
        ]
        result = engineer_query("PH", "京成小岩")

    print("result:", result)
    assert "マッチ案件なし" not in result, f"Expected match but got: {result}"
    assert "テスト案件A" in result
    print("test_skill_skip_engineer_matches_gross33_project: PASS")


def test_empty_required_skill_project_included():
    """必須スキル未設定案件が除外されないこと"""
    engineer = _make_engineer(rate=60, note="")
    project = _make_project(rate=70, req_skills=[], status="募集中")

    with patch.object(lq, 'fetch_all_pages') as mock_fetch:
        mock_fetch.side_effect = [
            [engineer],
            [project],
        ]
        result = engineer_query("PH", "京成小岩")

    assert "テスト案件A" in result, f"Empty-skill project should be included, got: {result}"
    print("test_empty_required_skill_project_included: PASS")


def test_gross_33_not_excluded():
    """gross=33の案件が除外されないこと (skill_skip=False, スキルマッチあり)"""
    engineer = _make_engineer(rate=37, skills=["PMO"], note="")
    project = _make_project(rate=70, req_skills=["PMO"], status="募集中")

    with patch.object(lq, 'fetch_all_pages') as mock_fetch:
        mock_fetch.side_effect = [
            [engineer],
            [project],
        ]
        result = engineer_query("PH", "京成小岩")

    assert "テスト案件A" in result, f"gross=33 should not be excluded, got: {result}"
    print("test_gross_33_not_excluded: PASS")


def test_negative_gross_excluded():
    """粗利マイナス案件が除外されること"""
    engineer = _make_engineer(rate=80, note="")
    project = _make_project(rate=70, req_skills=[], status="募集中")

    with patch.object(lq, 'fetch_all_pages') as mock_fetch:
        mock_fetch.side_effect = [
            [engineer],
            [project],
        ]
        result = engineer_query("PH", "京成小岩")

    assert "マッチ案件なし" in result, f"Negative gross should be excluded, got: {result}"
    print("test_negative_gross_excluded: PASS")


def test_stats_in_no_match_message():
    """0件時にstatsが含まれること"""
    engineer = _make_engineer(rate=60, skills=["Python"], note="")
    project = _make_project(rate=70, req_skills=["Java"], status="募集中")

    with patch.object(lq, 'fetch_all_pages') as mock_fetch:
        mock_fetch.side_effect = [
            [engineer],
            [project],
        ]
        result = engineer_query("PH", "京成小岩")

    assert "統計:" in result or "スキル除外" in result, f"Stats missing from no-match: {result}"
    print("test_stats_in_no_match_message: PASS")


if __name__ == "__main__":
    test_skill_skip_engineer_matches_gross33_project()
    test_empty_required_skill_project_included()
    test_gross_33_not_excluded()
    test_negative_gross_excluded()
    test_stats_in_no_match_message()
    print("\nAll matching logic tests PASSED")
