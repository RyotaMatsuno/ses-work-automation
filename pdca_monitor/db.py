"""SQLite wrapper for PC activity logs."""

from __future__ import annotations

import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "activity.db"

INTERVAL_MINUTES = 5
JST = timezone(timedelta(hours=9))

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    app_name TEXT,
    window_title TEXT,
    ocr_text TEXT,
    screenshot_path TEXT
);
"""

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]{2,}|[\u3040-\u30ff\u4e00-\u9fff]{2,}")
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "http",
    "https",
    "com",
    "www",
    "cursor",
    "windows",
    "microsoft",
    "file",
    "edit",
    "view",
}


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()


def insert_activity(
    timestamp: str,
    app_name: str | None,
    window_title: str | None,
    ocr_text: str | None,
    screenshot_path: str | None,
) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO activity_log
            (timestamp, app_name, window_title, ocr_text, screenshot_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (timestamp, app_name, window_title, ocr_text, screenshot_path),
        )
        conn.commit()


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _TOKEN_RE.finditer(text.lower()):
        token = match.group(0)
        if token in _STOPWORDS or token.isdigit():
            continue
        if len(token) < 2:
            continue
        tokens.append(token)
    return tokens


def get_weekly_summary(start_date: str, end_date: str) -> dict[str, Any]:
    """Aggregate one week of activity between inclusive ISO date strings (YYYY-MM-DD)."""
    init_db()
    start_ts = f"{start_date}T00:00:00"
    end_ts = f"{end_date}T23:59:59"

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT timestamp, app_name, window_title, ocr_text
            FROM activity_log
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp
            """,
            (start_ts, end_ts),
        ).fetchall()

    app_counts: Counter[str] = Counter()
    title_counts: Counter[str] = Counter()
    keyword_counts: Counter[str] = Counter()

    for row in rows:
        app = (row["app_name"] or "不明").strip() or "不明"
        app_counts[app] += INTERVAL_MINUTES

        title = (row["window_title"] or "").strip()
        if title:
            title_counts[title] += 1

        ocr = row["ocr_text"] or ""
        if ocr.strip():
            keyword_counts.update(_tokenize(ocr))

    app_usage = [{"app_name": name, "minutes": minutes} for name, minutes in app_counts.most_common()]
    top_titles = [{"window_title": title, "count": count} for title, count in title_counts.most_common(10)]
    top_keywords = [{"keyword": word, "count": count} for word, count in keyword_counts.most_common(20)]

    return {
        "start_date": start_date,
        "end_date": end_date,
        "record_count": len(rows),
        "app_usage": app_usage,
        "top_window_titles": top_titles,
        "top_keywords": top_keywords,
    }


def cleanup_old_records(days: int = 30) -> int:
    init_db()
    cutoff = (datetime.now(JST) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM activity_log WHERE timestamp < ?",
            (cutoff,),
        )
        conn.commit()
        return int(cur.rowcount)


def week_range_for_report(reference: datetime | None = None) -> tuple[str, str]:
    """Return Mon-Sun range for the week containing reference (JST)."""
    now = reference or datetime.now(JST)
    monday = (now - timedelta(days=now.weekday())).date()
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()
