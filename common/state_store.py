from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from common.io_utils import setup_stdout

setup_stdout()

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"

try:
    from dotenv import dotenv_values as _dotenv_values

    _ENV: dict = _dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}
except ImportError:
    _ENV = {}


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _ENV.get(name, default)


def _is_costguard_test_mode() -> bool:
    """COSTGUARD_TEST_MODE 判定。解析失敗時は fail-close で本番モード扱い。"""
    try:
        val = (_get_env("COSTGUARD_TEST_MODE", "") or "").strip().lower()
        return val in ("true", "1", "yes")
    except Exception:
        return False


def _state_dir() -> Path:
    raw = _get_env("STATE_DIR", "")
    if raw:
        return Path(os.path.expandvars(raw))
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        return Path(local) / "ses_work_state"
    return Path.home() / "AppData" / "Local" / "ses_work_state"


def _timeout_sec() -> int:
    try:
        return int(_get_env("SQLITE_TIMEOUT_SEC", "5"))
    except (TypeError, ValueError):
        return 5


def _configure_sqlite(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")


def get_db_path() -> Path:
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    if _is_costguard_test_mode():
        return d / "state_test.sqlite3"
    return d / "state.sqlite3"


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS daily_state(
    date TEXT PRIMARY KEY,
    daily_usd REAL NOT NULL DEFAULT 0,
    daily_calls INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS monthly_state(
    month TEXT PRIMARY KEY,
    monthly_usd REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS phase_calls(
    date TEXT,
    phase TEXT,
    reserved INTEGER NOT NULL DEFAULT 0,
    consumed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(date, phase)
);
CREATE TABLE IF NOT EXISTS reservations(
    reservation_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    phase TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finalized INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS dedup_claims(
    claim_id TEXT PRIMARY KEY,
    dedup_key TEXT NOT NULL UNIQUE,
    first_seen TEXT NOT NULL,
    ttl_sec INTEGER NOT NULL DEFAULT 3600,
    confirmed INTEGER NOT NULL DEFAULT 0,
    error INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS dedup_claims_archive(
    claim_id TEXT PRIMARY KEY,
    dedup_key TEXT NOT NULL,
    archived_at TEXT NOT NULL,
    error INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS event_log(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    reason TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    phase TEXT NOT NULL DEFAULT '',
    block_type TEXT NOT NULL DEFAULT '',
    script TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS pending_queue(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase TEXT NOT NULL,
    block_type TEXT NOT NULL DEFAULT '',
    target_id TEXT NOT NULL DEFAULT '',
    script TEXT NOT NULL DEFAULT '',
    queued_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
);
"""


def init_schema() -> None:
    """SPEC §8.2 の8テーブルを初期化する。"""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=_timeout_sec())
    try:
        _configure_sqlite(conn)
        conn.executescript(_SCHEMA_SQL)
    finally:
        conn.close()


def open_conn() -> sqlite3.Connection:
    """autocommit モードの接続を返す。BEGIN IMMEDIATE は呼び出し側が発行する。"""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path), timeout=_timeout_sec(), isolation_level=None)
    conn.row_factory = sqlite3.Row
    _configure_sqlite(conn)
    return conn


@contextmanager
def immediate_tx(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """BEGIN IMMEDIATE トランザクション。失敗時は ROLLBACK して例外を再送出する。
    OperationalError("database is locked") は呼び出し側でキャッチすること。
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise


@contextmanager
def begin_immediate() -> Iterator[sqlite3.Connection]:
    """接続を開き BEGIN IMMEDIATE トランザクションを管理する（SPEC v2.10.1 §5.2）。"""
    init_schema()
    conn = open_conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.close()
