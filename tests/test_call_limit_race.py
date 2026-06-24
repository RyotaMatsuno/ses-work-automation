"""8.6 DAILY_CALL_LIMIT 2プロセス並行テスト（sqlite BEGIN IMMEDIATE で排他）。"""

from __future__ import annotations

import multiprocessing
import os
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent


def _worker(state_dir: str, limit: int, results: list) -> None:
    """子プロセスで reserve を試みる。"""
    os.environ["STATE_DIR"] = state_dir
    sys.path.insert(0, str(BASE_DIR))
    try:
        import common.state_store as ss

        # キャッシュをクリア
        ss._ENV.pop("STATE_DIR", None)
        from common.ledger import reserve

        rid = reserve("research")
        results.append(rid)
    except Exception:
        results.append(None)


def _worker_mp(state_dir, limit, result_queue):
    os.environ["STATE_DIR"] = state_dir
    sys.path.insert(0, str(BASE_DIR))
    try:
        from common.ledger import reserve

        rid = reserve("research")
        result_queue.put(rid)
    except Exception:
        result_queue.put(None)


@pytest.mark.timeout(30)
def test_race_only_one_gets_last_slot(tmp_path, monkeypatch):
    """DAILY_CALL_LIMIT=1 のとき2プロセスが同時に reserve を呼んでも1つしか成功しない。"""
    monkeypatch.setenv("DAILY_CALL_LIMIT_DEFAULT", "1")
    state_dir = str(tmp_path / "ses_work_state")
    os.makedirs(state_dir, exist_ok=True)

    # スキーマ初期化
    os.environ["STATE_DIR"] = state_dir
    from common.state_store import init_schema

    init_schema()

    ctx = multiprocessing.get_context("spawn")
    q = ctx.Queue()
    p1 = ctx.Process(target=_worker_mp, args=(state_dir, 1, q))
    p2 = ctx.Process(target=_worker_mp, args=(state_dir, 1, q))
    p1.start()
    p2.start()
    p1.join(timeout=20)
    p2.join(timeout=20)

    results = [q.get_nowait() for _ in range(2)]
    non_none = [r for r in results if r is not None]
    assert len(non_none) == 1, f"Expected exactly 1 success, got {non_none}"
