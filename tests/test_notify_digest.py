"""通知ダイジェスト化 + target_file任意化 のテスト。"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


# ── helpers ────────────────────────────────────────────────────────────────


def _write_queue(q: Path, events: list[dict]) -> None:
    q.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
        encoding="utf-8",
    )


# ── enqueue tests ──────────────────────────────────────────────────────────


def test_notify_success_enqueues_not_pushes(tmp_path, monkeypatch):
    """notify_success はキューに追記し、即時pushしない。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        m.notify_success("foo.md", 0.01, 120.0)

    mock_push.assert_not_called()
    e = json.loads(q.read_text(encoding="utf-8").strip())
    assert e["type"] == "success"
    assert e["task"] == "foo.md"
    assert e["cost_usd"] == pytest.approx(0.01)
    assert e["duration_sec"] == pytest.approx(120.0)


def test_notify_retry_enqueues_not_pushes(tmp_path, monkeypatch):
    """notify_retry はキューに追記し、即時pushしない。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        m.notify_retry("bar__try1.md", 1, "exit=1")

    mock_push.assert_not_called()
    e = json.loads(q.read_text(encoding="utf-8").strip())
    assert e["type"] == "retry"
    assert e["try_num"] == 1
    assert e["reason"] == "exit=1"


def test_notify_blocked_enqueues_not_pushes(tmp_path, monkeypatch):
    """notify_blocked はキューに追記し、即時pushしない。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        m.notify_blocked("baz__try2.md", "repeated failure")

    mock_push.assert_not_called()
    e = json.loads(q.read_text(encoding="utf-8").strip())
    assert e["type"] == "blocked"


def test_notify_timeout_enqueues_not_pushes(tmp_path, monkeypatch):
    """notify_timeout はキューに追記し、即時pushしない。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        m.notify_timeout("timeout_task.md")

    mock_push.assert_not_called()
    e = json.loads(q.read_text(encoding="utf-8").strip())
    assert e["type"] == "timeout"
    assert e["task"] == "timeout_task.md"


def test_notify_cost_guard_is_immediate(monkeypatch):
    """notify_cost_guard は即時push（例外的な重大アラート）。"""
    import task_auto_runner.notifier as m

    with patch.object(m, "push_message") as mock_push:
        m.notify_cost_guard(145.0)

    mock_push.assert_called_once()
    assert "140超" in mock_push.call_args[0][0]


# ── flush tests ────────────────────────────────────────────────────────────


def test_flush_sends_digest_and_clears_queue(tmp_path, monkeypatch):
    """flush_notify_queue: 複数イベントを1通で送信し、キューを空にする。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    _write_queue(q, [
        {"ts": "2026-07-06T10:00:00", "type": "success", "task": "t1.md", "cost_usd": 0.01, "duration_sec": 90},
        {"ts": "2026-07-06T11:00:00", "type": "retry", "task": "t2__try1.md", "try_num": 1, "reason": "exit=1"},
        {"ts": "2026-07-06T11:30:00", "type": "blocked", "task": "t3__try2.md", "reason": "gate NG x2"},
    ])
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        result = m.flush_notify_queue(label="12:00")

    assert result is True
    mock_push.assert_called_once()
    text = mock_push.call_args[0][0]
    assert "12:00" in text
    assert "完了1" in text
    assert "再投入1" in text
    assert "blocked 1" in text
    assert "t1.md" in text
    assert "t2__try1.md" in text
    assert "t3__try2.md" in text
    # 消し込み確認
    assert q.read_text(encoding="utf-8") == ""


def test_flush_zero_events_skips_push(tmp_path, monkeypatch):
    """イベント0件なら送信せずFalseを返す。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    q.write_text("", encoding="utf-8")
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        result = m.flush_notify_queue(label="18:00")

    assert result is False
    mock_push.assert_not_called()


def test_flush_no_queue_file_skips_push(tmp_path, monkeypatch):
    """キューファイルが存在しない場合も送信せずFalseを返す。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        result = m.flush_notify_queue(label="12:00")

    assert result is False
    mock_push.assert_not_called()


def test_flush_sends_once_regardless_of_event_count(tmp_path, monkeypatch):
    """イベントが何件あっても送信は1回（1通のLINEメッセージ）。"""
    import task_auto_runner.notifier as m

    q = tmp_path / "notify_queue.jsonl"
    events = [
        {"ts": f"2026-07-06T0{i}:00:00", "type": "success", "task": f"t{i}.md", "cost_usd": 0.01, "duration_sec": 60}
        for i in range(5)
    ]
    _write_queue(q, events)
    monkeypatch.setattr(m, "NOTIFY_QUEUE", q)

    with patch.object(m, "push_message") as mock_push:
        result = m.flush_notify_queue(label="12:00")

    assert result is True
    assert mock_push.call_count == 1
    assert "完了5" in mock_push.call_args[0][0]


# ── target_file任意化テスト ────────────────────────────────────────────────


def test_gate_skip_when_target_file_empty():
    """target_file が空文字ならゲートをスキップしてOKを返す。"""
    from task_auto_runner.gate_runner import run_gate_check

    result = run_gate_check("", phase="implementation")
    assert result.verdict == "OK"
    assert result.judgment == "SKIP"
    assert "未指定" in result.reason


def test_gate_ng_when_target_file_specified_but_missing():
    """target_file が指定されているがファイルが存在しない場合はNG。"""
    from task_auto_runner.gate_runner import run_gate_check

    result = run_gate_check("/nonexistent/path/file.py", phase="implementation")
    assert result.verdict == "NG"
    assert "not found" in result.reason


def test_extract_target_file_returns_empty_when_no_field():
    """対象ファイル/ディレクトリ指定なしの指示書は空文字を返す。"""
    from task_auto_runner.gate_runner import extract_target_file

    text = "# タスク\n## 作業内容\nfoo bar baz"
    assert extract_target_file(text) == ""


def test_extract_target_file_empty_value_returns_empty():
    """対象ファイル:（値が空）も空文字を返す（誤NGを起こさない）。"""
    from task_auto_runner.gate_runner import extract_target_file

    text = "対象ファイル:\n## 作業内容\nfoo bar"
    result = extract_target_file(text)
    # 値が空なので存在チェックで弾かれ "" が返る
    assert result == ""
