"""8.7 dedup claim 2プロセス並行テスト（UNIQUE 違反検知）。"""

from __future__ import annotations

import multiprocessing
import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent


def _claim_worker(state_dir: str, key: str, result_queue) -> None:
    os.environ["STATE_DIR"] = state_dir
    sys.path.insert(0, str(BASE_DIR))
    try:
        from common.dedup import claim_dedup

        claim_id = claim_dedup(key)
        result_queue.put(claim_id)
    except Exception:
        result_queue.put(None)


@pytest.mark.timeout(30)
def test_race_only_one_claim_wins(tmp_path, monkeypatch):
    """同一 dedup_key を2プロセスが同時に claim しても1つだけ成功する。"""
    state_dir = str(tmp_path / "ses_work_state")
    os.makedirs(state_dir, exist_ok=True)
    os.environ["STATE_DIR"] = state_dir

    from common.state_store import init_schema

    init_schema()

    key = "2026-06-17:skill_judge:research:race-proj-001"
    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()

    p1 = ctx.Process(target=_claim_worker, args=(state_dir, key, q))
    p2 = ctx.Process(target=_claim_worker, args=(state_dir, key, q))
    p1.start()
    p2.start()
    p1.join(timeout=20)
    p2.join(timeout=20)

    results = [q.get_nowait() for _ in range(2)]
    successes = [r for r in results if r is not None]
    failures = [r for r in results if r is None]
    assert len(successes) == 1, f"Expected exactly 1 winner, got {successes}"
    assert len(failures) == 1, "Expected exactly 1 loser"
