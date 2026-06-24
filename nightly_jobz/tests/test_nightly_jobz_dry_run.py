# -*- coding: utf-8 -*-
"""nightly_jobz Phase 1 tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SES_WORK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SES_WORK))

from nightly_jobz import config
from nightly_jobz.notion_queue import QueueTask
from nightly_jobz.task_processor import dispatch_task, process_stub_blocked


@pytest.fixture
def tmp_logs(tmp_path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(config, "LOG_DIR", log_dir)
    monkeypatch.setattr(config, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path / "research")
    return log_dir


def test_dispatch_investigation_dry_run(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RESEARCH_DIR", tmp_path / "research")
    task = QueueTask(
        page_id="p1",
        task_id="T-INV-1",
        task_type="investigation",
        status="queued",
        input_data="案件タイマーの最適値を調査",
    )
    run_cost = config.RunCostTracker(limit_usd=2.0)
    result = dispatch_task(task, dry_run=True, run_cost=run_cost)
    assert result.status == "done"
    assert result.task_type == "investigation"
    assert result.cost_usd == 0.0


def test_dispatch_spec_design_dry_run(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DRAFTS_DIR", tmp_path / "drafts")
    task = QueueTask(
        page_id="p2",
        task_id="T-SPEC-1",
        task_type="spec_design",
        status="queued",
        input_data="nightly_jobz Phase 2 の要件",
    )
    result = dispatch_task(task, dry_run=True, run_cost=config.RunCostTracker())
    assert result.status == "review"
    assert "松野確認" in result.note


def test_stub_matching_blocked_dry_run():
    task = QueueTask(
        page_id="p3",
        task_id="T-MATCH-1",
        task_type="matching",
        status="queued",
        input_data="",
    )
    result = process_stub_blocked(task, dry_run=True)
    assert result.status == "blocked"


@patch("nightly_jobz.nightly_jobz.fetch_queued_tasks")
@patch("nightly_jobz.nightly_jobz.acquire_lock")
@patch("nightly_jobz.nightly_jobz.release_lock")
def test_run_nightly_dry_run_generates_briefing(
    mock_release,
    mock_acquire,
    mock_fetch,
    tmp_logs,
    monkeypatch,
):
    mock_acquire.return_value = MagicMock()
    mock_fetch.return_value = [
        QueueTask("p1", "T1", "investigation", "queued", "調査依頼"),
        QueueTask("p2", "T2", "matching", "queued", ""),
    ]
    monkeypatch.setattr(config, "DRY_RUN", True)

    from nightly_jobz.nightly_jobz import run_nightly

    briefing = run_nightly(dry_run=True)
    assert briefing["dry_run"] is True
    assert briefing["tasks_processed"] == 2
    assert briefing["tasks_done"] == 1
    assert briefing["tasks_blocked"] == 1

    briefing_files = list(tmp_logs.glob("briefing_*.json"))
    assert len(briefing_files) == 1
    saved = json.loads(briefing_files[0].read_text(encoding="utf-8"))
    assert saved["tasks_processed"] == 2


def test_lock_skip_on_second_acquire(monkeypatch):
    from nightly_jobz import nightly_jobz as nj

    monkeypatch.setattr(nj, "_setup_logging", lambda: Path("x"))
    monkeypatch.setattr(nj, "_rotate_logs", lambda: None)
    monkeypatch.setattr(nj, "run_nightly", lambda **_: {"ok": True})
    monkeypatch.setattr(config, "load_env", lambda: None)

    calls = {"release": 0}
    monkeypatch.setattr(nj, "release_lock", lambda: calls.__setitem__("release", calls["release"] + 1))

    def boom():
        raise RuntimeError("lock_exists")

    monkeypatch.setattr(nj, "acquire_lock", boom)
    assert nj.main() == 0
