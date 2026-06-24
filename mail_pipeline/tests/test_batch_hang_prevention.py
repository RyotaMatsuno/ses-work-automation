# -*- coding: utf-8 -*-
"""Task BE: Batch API ハング再発防止のテスト。"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from mail_pipeline import mail_pipeline as mp


@pytest.fixture()
def lock_env(monkeypatch: pytest.MonkeyPatch) -> Path:
    tmp = Path(os.environ.get("TEMP", ".")) / f"lock_test_{os.getpid()}"
    tmp.mkdir(parents=True, exist_ok=True)
    lock_file = tmp / "pipeline.lock"
    monkeypatch.setenv("LOCALAPPDATA", str(tmp))
    monkeypatch.setattr(mp, "LOCK_FILE", str(lock_file))
    return lock_file


def test_stale_lock_removed_after_ttl(lock_env: Path) -> None:
    """45分超の lock ファイルが自動解除され、新規プロセスがロック取得できる。"""
    lock_env.write_text("stale", encoding="utf-8")
    stale_mtime = time.time() - (mp.LOCK_TTL_MINUTES + 5) * 60
    os.utime(lock_env, (stale_mtime, stale_mtime))

    fh = mp.acquire_lock()
    try:
        assert lock_env.exists()
        assert fh is not None
    finally:
        fh.close()


def test_fresh_lock_blocks_second_acquire(lock_env: Path) -> None:
    """TTL 内の lock は従来どおり二重起動を防ぐ。"""
    first = mp.acquire_lock()
    try:
        with pytest.raises(SystemExit) as exc:
            mp.acquire_lock()
        assert exc.value.code == 0
    finally:
        first.close()


def test_wait_for_batch_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """ポーリング上限超過で None を返す。"""
    monkeypatch.setattr(mp, "BATCH_POLL_TIMEOUT_MINUTES", 0)
    monkeypatch.setattr(mp, "BATCH_POLL_INTERVAL_SEC", 0)

    mock_get = MagicMock(
        return_value=MagicMock(status_code=200, json=lambda: {"processing_status": "in_progress"})
    )
    monkeypatch.setattr(mp.requests, "get", mock_get)

    result = mp.wait_for_batch("batch_test_123", headers={"x-api-key": "test"})
    assert result is None
    assert mock_get.called


def test_mark_batch_requests_pending() -> None:
    """未処理の batch リクエストが pending にマークされる。"""
    results: dict = {}
    batch_requests = [{"custom_id": "classify_0"}, {"custom_id": "classify_1"}]
    mp._mark_batch_requests_pending(batch_requests, results)
    assert results[0]["type"] == "pending"
    assert results[1]["type"] == "pending"


@patch("mail_pipeline.mail_pipeline.finalize")
@patch("mail_pipeline.mail_pipeline.wait_for_batch", return_value=None)
@patch("mail_pipeline.mail_pipeline._batch_budget_reserve")
@patch("mail_pipeline.mail_pipeline.requests.post")
@patch("analyze_final.classify_by_rule", return_value="other")
def test_classify_v2_batch_timeout_marks_pending(
    _mock_rule: MagicMock,
    mock_post: MagicMock,
    mock_reserve: MagicMock,
    _mock_wait: MagicMock,
    _mock_finalize: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch タイムアウト時、未分類メールが pending 扱いになる（次回再処理）。"""
    monkeypatch.setattr(mp, "ANTHROPIC_KEY", "sk-test")
    mock_reserve.return_value = SimpleNamespace(allowed=True)
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"id": "batch_timeout_id"})

    emails = [{"index": 0, "subject": "案件のご紹介", "body": "Java開発", "sender": "a@b.com", "msg_id": "m1"}]
    results = mp.classify_email_v2(emails)

    assert results[0]["type"] == "pending"
