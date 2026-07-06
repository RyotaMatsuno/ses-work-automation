"""LINE通知分岐テスト（OK時: pushゼロ / NG時: 1行のみ）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

GATE_CHECKER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GATE_CHECKER_DIR))
sys.path.insert(0, str(GATE_CHECKER_DIR.parent))

import gate_check


_ENV_WITH_LINE = {
    "OPENAI_API_KEY": "test-key",
    "LINE_CHANNEL_ACCESS_TOKEN": "line-token",
    "MATSUNO_USER_ID": "U_matsuno",
}


def _fake_dual_review(review_text: str, judgment: str, verdict: str) -> mock.Mock:
    decision = mock.Mock()
    decision.adopted_result.text = review_text
    decision.final_judgment = judgment
    decision.final_verdict = verdict
    decision.gpt_result.text = review_text
    decision.gpt_result.judgment = judgment
    decision.sonnet_result.text = review_text
    decision.sonnet_result.judgment = judgment
    decision.sonnet_result.verdict = verdict
    decision.sonnet_available = True
    decision.agreement = True
    return decision


def _run_gate_with_mocks(
    tmp_path: Path,
    *,
    review_text: str,
    judgment: str,
    verdict: str,
) -> mock.Mock:
    target = tmp_path / "src" / "feature.py"
    target.parent.mkdir(parents=True)
    target.write_text("# sample", encoding="utf-8")

    with mock.patch.object(gate_check, "check_daily_limit", return_value=(True, 0)):
        with mock.patch.object(
            gate_check,
            "run_dual_review",
            return_value=_fake_dual_review(review_text, judgment, verdict),
        ):
            with mock.patch.object(gate_check, "increment_daily_counter", return_value=1):
                with mock.patch.object(gate_check, "_load_env", return_value=_ENV_WITH_LINE):
                    with mock.patch.object(gate_check, "save_result", return_value=tmp_path / "out.json"):
                        with mock.patch.object(gate_check, "send_line_notification") as send_mock:
                            gate_check.run_gate_check("implementation", str(target), None, None)
                            return send_mock


def test_ok_verdict_never_calls_send_line_notification(tmp_path: Path) -> None:
    send_mock = _run_gate_with_mocks(
        tmp_path,
        review_text="問題なし\n【判定: GO】\nHUMAN_REVIEW: YES",
        judgment="GO",
        verdict="OK",
    )
    send_mock.assert_not_called()


def test_ng_verdict_calls_send_line_notification_once(tmp_path: Path) -> None:
    send_mock = _run_gate_with_mocks(
        tmp_path,
        review_text="重大な問題\n【判定: NG】\nHUMAN_REVIEW: NO",
        judgment="NG",
        verdict="NG",
    )
    send_mock.assert_called_once_with(
        phase="implementation",
        target=str(tmp_path / "src" / "feature.py"),
        env=_ENV_WITH_LINE,
    )


def test_ng_verdict_human_review_still_sends_one_line(tmp_path: Path) -> None:
    send_mock = _run_gate_with_mocks(
        tmp_path,
        review_text="仕様確認が必要\n【判定: NG】\nHUMAN_REVIEW: YES",
        judgment="NG",
        verdict="NG",
    )
    send_mock.assert_called_once()


def test_send_line_notification_message_is_single_line(tmp_path: Path) -> None:
    captured: dict[str, bytes] = {}

    class FakeResponse:
        status = 200

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    def fake_urlopen(request: object, timeout: int = 10) -> FakeResponse:
        captured["body"] = getattr(request, "data", b"")
        return FakeResponse()

    target = tmp_path / "proj" / "gate_check.py"
    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        ok = gate_check.send_line_notification(
            phase="implementation",
            target=str(target),
            env=_ENV_WITH_LINE,
        )

    assert ok is True
    payload = json.loads(captured["body"].decode("utf-8"))
    message = payload["messages"][0]["text"]
    assert message == "[gate] implementation NG: gate_check.py → ジョブズ対応中・返信不要"
    assert "\n" not in message
    assert "ok" not in message.lower() or "返信不要" in message
    assert "松野確認" not in message
    assert "送ってください" not in message


def test_send_line_notification_skips_without_credentials(caplog: pytest.LogCaptureFixture) -> None:
    with mock.patch("urllib.request.urlopen") as urlopen_mock:
        ok = gate_check.send_line_notification(
            phase="design",
            target="SPEC.md",
            env={"OPENAI_API_KEY": "k"},
        )

    assert ok is False
    urlopen_mock.assert_not_called()


def test_target_filename_extracts_basename_only() -> None:
    assert gate_check._target_filename("/path/to/my_module.py") == "my_module.py"
    assert gate_check._target_filename("") == "(不明)"
