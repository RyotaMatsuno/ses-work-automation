from __future__ import annotations

import sys
from pathlib import Path

GATE_CHECKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE_CHECKER_DIR))

from gate_check import needs_human_review, parse_judgment, resolve_human_review

# 層1/2が反応しやすい語（契約グループの同義語）
_KEYWORD_NOISE = "請求・単価の記述はレビュー本文に含まれますが、実害はありません。"


def _resolved(review_text: str, phase: str = "requirements") -> tuple[str, str, bool]:
    judgment, verdict = parse_judgment(review_text)
    return judgment, verdict, resolve_human_review(verdict, phase, review_text)


def test_ok_with_human_review_no_suppresses_keyword_false_positive():
    review_text = f"""
{_KEYWORD_NOISE}
【判定: GO】
HUMAN_REVIEW: NO
"""
    assert needs_human_review("requirements", review_text) is True
    _, verdict, human_review = _resolved(review_text)
    assert verdict == "OK"
    assert human_review is False


def test_ok_with_human_review_yes_stays_true():
    review_text = f"""
{_KEYWORD_NOISE}
【判定: GO】
HUMAN_REVIEW: YES
"""
    _, verdict, human_review = _resolved(review_text)
    assert verdict == "OK"
    assert human_review is True


def test_ng_with_human_review_no_runs_wall_hitting_path():
    review_text = """
実装着手不可の重大問題があります。
【判定: NG】
HUMAN_REVIEW: NO
"""
    _, verdict, human_review = _resolved(review_text)
    assert verdict == "NG"
    assert human_review is False


def test_ng_with_human_review_yes_stays_true():
    review_text = """
実装着手不可の重大問題があります。
【判定: NG】
HUMAN_REVIEW: YES
"""
    _, verdict, human_review = _resolved(review_text)
    assert verdict == "NG"
    assert human_review is True


def test_conditional_go_with_human_review_no_suppresses_false_positive():
    review_text = f"""
{_KEYWORD_NOISE}
【判定: 条件付きGO】
HUMAN_REVIEW: NO
"""
    judgment, verdict, human_review = _resolved(review_text)
    assert judgment == "条件付きGO"
    assert verdict == "OK"
    assert human_review is False


def test_layer1_keyword_cost_occurrence():
    assert needs_human_review("requirements", "費用が発生します") is True


def test_layer1_keyword_contract_change():
    assert needs_human_review("requirements", "契約変更が必要") is True


def test_layer2_synonym_cost_increase():
    assert needs_human_review("requirements", "コストが増える") is True


def test_layer3_missing_human_review_line_defaults_safe():
    review_text = "問題は見つかりませんでした。【判定: GO】"
    assert needs_human_review("requirements", review_text) is True


def test_layer3_human_review_no_without_keywords():
    review_text = "問題は見つかりませんでした。【判定: GO】\nHUMAN_REVIEW: NO"
    assert needs_human_review("requirements", review_text) is False
