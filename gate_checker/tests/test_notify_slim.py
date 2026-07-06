"""Task 01: LINE通知絞り込み（OK時ゼロ / NG時1行のみ）のユニットテスト。"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

GATE_CHECKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE_CHECKER_DIR))
sys.path.insert(0, str(GATE_CHECKER_DIR.parent))

import gate_check


def _make_decision(verdict: str, judgment: str) -> mock.Mock:
    text = f"テストレビュー\n【判定: {judgment}】\nHUMAN_REVIEW: NO"
    d = mock.Mock()
    d.adopted_result.text = text
    d.final_judgment = judgment
    d.final_verdict = verdict
    d.gpt_result.text = text
    d.gpt_result.judgment = judgment
    d.sonnet_result.text = text
    d.sonnet_result.judgment = judgment
    d.sonnet_result.verdict = verdict
    d.sonnet_available = True
    d.agreement = True
    return d


def _run(tmp_path: Path, verdict: str, judgment: str) -> tuple[int, list[tuple]]:
    """run_gate_check を最小mockで実行し、send_line_notification の呼び出し引数を返す。"""
    spec_file = tmp_path / "SPEC.md"
    spec_file.write_text("# Test SPEC", encoding="utf-8")

    calls: list[tuple] = []

    def capture(*args, **kwargs):
        calls.append((args, kwargs))
        return True

    with (
        mock.patch.object(gate_check, "run_dual_review", return_value=_make_decision(verdict, judgment)),
        mock.patch.object(gate_check, "check_daily_limit", return_value=(True, 0)),
        mock.patch.object(gate_check, "increment_daily_counter", return_value=1),
        mock.patch.object(gate_check, "_load_env", return_value={
            "OPENAI_API_KEY": "fake",
            "LINE_CHANNEL_ACCESS_TOKEN": "tok",
            "MATSUNO_USER_ID": "uid",
        }),
        mock.patch.object(gate_check, "save_result", return_value=tmp_path / "result.json"),
        mock.patch.object(gate_check, "send_line_notification", side_effect=capture),
        mock.patch.object(gate_check, "run_wall_hitting", return_value=("", tmp_path / "wall.txt")),
    ):
        rc = gate_check.run_gate_check("requirements", str(spec_file), None, None)

    return rc, calls


def test_ok_verdict_no_line_push(tmp_path: Path) -> None:
    """OK判定時に send_line_notification が一切呼ばれない。"""
    rc, calls = _run(tmp_path, verdict="OK", judgment="GO")
    assert rc == 0
    assert calls == [], "OK時にLINE push が発生している"


def test_ng_verdict_sends_exactly_once(tmp_path: Path) -> None:
    """NG判定時に send_line_notification がちょうど1回呼ばれる。"""
    rc, calls = _run(tmp_path, verdict="NG", judgment="NG")
    assert rc == 1
    assert len(calls) == 1, f"NG時の push 呼び出し回数が {len(calls)} 回（期待: 1回）"


def test_ng_message_is_single_line(tmp_path: Path) -> None:
    """NG通知メッセージが1行（改行なし）であることを確認。"""
    _, calls = _run(tmp_path, verdict="NG", judgment="NG")
    # send_line_notification 内部で生成されるメッセージを検証するため
    # NOTIFY_TEMPLATE_NG のフォーマットをテスト
    template = gate_check.NOTIFY_TEMPLATE_NG
    filename = "SPEC.md"
    msg = template.format(phase="requirements", filename=filename)
    assert "\n" not in msg, f"メッセージに改行が含まれている: {msg!r}"


def test_ng_message_no_reply_request(tmp_path: Path) -> None:
    """NGメッセージに返信要求フレーズが含まれない。"""
    template = gate_check.NOTIFY_TEMPLATE_NG
    msg = template.format(phase="requirements", filename="SPEC.md")
    reply_phrases = ["okと送", "gate ok", "okと返信", "お願いします", "確認後"]
    for phrase in reply_phrases:
        assert phrase not in msg, f"返信要求フレーズ '{phrase}' が含まれています: {msg!r}"


def test_ng_message_contains_required_parts(tmp_path: Path) -> None:
    """NGメッセージに [gate] / NG / ジョブズ対応中・返信不要 が含まれる。"""
    template = gate_check.NOTIFY_TEMPLATE_NG
    msg = template.format(phase="implementation", filename="matcher.py")
    assert "[gate]" in msg
    assert "NG" in msg
    assert "ジョブズ対応中・返信不要" in msg
    assert "implementation" in msg
    assert "matcher.py" in msg
