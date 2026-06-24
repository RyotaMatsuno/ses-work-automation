# -*- coding: utf-8 -*-
"""state_store SQLite WAL configuration tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import state_store as ss


@pytest.fixture
def state_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_dir = tmp_path / "state"
    db_dir.mkdir()
    monkeypatch.setenv("STATE_DIR", str(db_dir))
    monkeypatch.setattr(ss, "_ENV", {})
    return db_dir / "state.sqlite3"


def test_state_store_wal_mode_enabled(state_db: Path) -> None:
    ss.init_schema()
    conn = ss.open_conn()
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode.lower() == "wal"
        assert state_db.exists()
    finally:
        conn.close()


def test_state_store_concurrent_writes(state_db: Path) -> None:
    import threading

    ss.init_schema()
    errors: list[Exception] = []

    def writer(idx: int) -> None:
        try:
            with ss.begin_immediate() as conn:
                conn.execute(
                    """
                    INSERT INTO event_log(timestamp, reason, detail, phase, block_type, script)
                    VALUES (?, ?, ?, '', '', 'test')
                    """,
                    (f"2026-06-19T10:00:{idx:02d}", f"reason-{idx}", f"detail-{idx}"),
                )
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    conn = ss.open_conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM event_log").fetchone()[0]
        assert count == 10
    finally:
        conn.close()
