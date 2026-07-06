from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "matching_v3_processed.db"


class ProcessedDB:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def is_processed(self, case_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT business_status, retry_count FROM processed_cases WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if row is None:
            return False
        if row["business_status"] == "ERROR" and (row["retry_count"] or 0) < 3:
            return False
        return True

    def should_skip_unchanged_case(self, case_id: str, last_edited_at: str = "") -> bool:
        """処理済みかつ案件の last_edited が変わっていなければスキップ。"""
        if not self.is_processed(case_id):
            return False
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT business_status, case_last_edited_at
                FROM processed_cases WHERE case_id = ?
                """,
                (case_id,),
            ).fetchone()
        if row is None:
            return False
        if row["business_status"] not in ("matched", "ng", "SKIPPED"):
            return False
        stored = row["case_last_edited_at"] or ""
        if last_edited_at and stored:
            return last_edited_at == stored
        return True

    def record_extraction_retry(self, count: int = 1) -> None:
        if count <= 0:
            return
        with self._connect() as conn:
            self._increment_daily_stat(conn, extraction_retry_count=count)

    def increment_retry(self, case_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE processed_cases
                SET retry_count = COALESCE(retry_count, 0) + 1,
                    updated_at = datetime('now', '+9 hours')
                WHERE case_id = ?
                """,
                (case_id,),
            )

    def mark_api_called(self, case_id: str, subject: str, date: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO processed_cases (
                    case_id, email_subject, email_date, api_called,
                    api_called_at, business_status, updated_at
                )
                VALUES (?, ?, ?, 1, datetime('now', '+9 hours'), 'processing', datetime('now', '+9 hours'))
                ON CONFLICT(case_id) DO UPDATE SET
                    email_subject = excluded.email_subject,
                    email_date = excluded.email_date,
                    api_called = 1,
                    api_called_at = excluded.api_called_at,
                    business_status = 'processing',
                    updated_at = excluded.updated_at
                """,
                (case_id, subject, date),
            )
            self._increment_daily_stat(conn, api_calls=1)

    def update_status(
        self,
        case_id: str,
        status: str,
        results: list[Any] | None = None,
        case_last_edited_at: str | None = None,
    ) -> None:
        results_json = json.dumps(results, ensure_ascii=False) if results is not None else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO processed_cases (
                    case_id, business_status, match_results_json, case_last_edited_at, updated_at
                )
                VALUES (?, ?, ?, ?, datetime('now', '+9 hours'))
                ON CONFLICT(case_id) DO UPDATE SET
                    business_status = excluded.business_status,
                    match_results_json = COALESCE(excluded.match_results_json, processed_cases.match_results_json),
                    case_last_edited_at = COALESCE(excluded.case_last_edited_at, processed_cases.case_last_edited_at),
                    updated_at = excluded.updated_at
                """,
                (case_id, status, results_json, case_last_edited_at),
            )

    def record_staleness_excluded(self, count: int) -> None:
        if count <= 0:
            return
        with self._connect() as conn:
            self._increment_daily_stat(conn, staleness_excluded_count=count)

    def record_oov_skip(self, count: int = 1) -> None:
        if count <= 0:
            return
        with self._connect() as conn:
            self._increment_daily_stat(conn, oov_skip_count=count)

    def recompute_daily_stats(self, stat_date: str | None = None) -> dict[str, int | float | str]:
        """processed_cases から daily_stats を再集計して冪等 upsert する。"""
        with self._connect() as conn:
            if stat_date is None:
                stat_date = conn.execute("SELECT date('now', '+9 hours') AS d").fetchone()["d"]

            match_count = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM processed_cases
                    WHERE date(updated_at) = ? AND business_status = 'matched'
                    """,
                    (stat_date,),
                ).fetchone()[0]
            )
            ng_count = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM processed_cases
                    WHERE date(updated_at) = ? AND lower(business_status) = 'ng'
                    """,
                    (stat_date,),
                ).fetchone()[0]
            )
            review_count = 0
            for row in conn.execute(
                """
                SELECT match_results_json FROM processed_cases
                WHERE date(updated_at) = ? AND match_results_json IS NOT NULL
                """,
                (stat_date,),
            ):
                try:
                    results = json.loads(row["match_results_json"])
                except (json.JSONDecodeError, TypeError):
                    continue
                if isinstance(results, list) and any(
                    isinstance(item, dict) and item.get("verdict") == "REVIEW" for item in results
                ):
                    review_count += 1

            api_calls = int(
                conn.execute(
                    """
                    SELECT COUNT(*) FROM processed_cases
                    WHERE date(updated_at) = ? AND api_called = 1
                    """,
                    (stat_date,),
                ).fetchone()[0]
            )
            total_cost_usd = float(
                conn.execute(
                    """
                    SELECT COALESCE(SUM(total_cost_usd), 0) FROM processed_cases
                    WHERE date(updated_at) = ?
                    """,
                    (stat_date,),
                ).fetchone()[0]
            )
            existing_staleness_row = conn.execute(
                "SELECT staleness_excluded_count FROM daily_stats WHERE stat_date = ?",
                (stat_date,),
            ).fetchone()
            staleness_excluded_count = (
                int(existing_staleness_row["staleness_excluded_count"] or 0)
                if existing_staleness_row
                else 0
            )

            conn.execute(
                """
                INSERT INTO daily_stats (
                    stat_date, api_calls, total_cost_usd, ng_count, review_count, match_count,
                    staleness_excluded_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stat_date) DO UPDATE SET
                    api_calls = excluded.api_calls,
                    total_cost_usd = excluded.total_cost_usd,
                    ng_count = excluded.ng_count,
                    review_count = excluded.review_count,
                    match_count = excluded.match_count,
                    staleness_excluded_count = COALESCE(
                        daily_stats.staleness_excluded_count, excluded.staleness_excluded_count
                    )
                """,
                (stat_date, api_calls, total_cost_usd, ng_count, review_count, match_count, staleness_excluded_count),
            )

        return {
            "stat_date": stat_date,
            "api_calls": api_calls,
            "total_cost_usd": total_cost_usd,
            "ng_count": ng_count,
            "review_count": review_count,
            "match_count": match_count,
            "staleness_excluded_count": staleness_excluded_count,
        }

    def backfill_daily_stats(self) -> list[dict[str, int | float | str]]:
        """processed_cases に存在する全日付の daily_stats を再計算する。"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT date(updated_at) AS stat_date
                FROM processed_cases
                WHERE updated_at IS NOT NULL
                ORDER BY stat_date
                """
            ).fetchall()
        return [self.recompute_daily_stats(row["stat_date"]) for row in rows]

    def add_cost(self, case_id: str, cost_usd: float) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO processed_cases (case_id, total_cost_usd, updated_at)
                VALUES (?, ?, datetime('now', '+9 hours'))
                ON CONFLICT(case_id) DO UPDATE SET
                    total_cost_usd = processed_cases.total_cost_usd + excluded.total_cost_usd,
                    updated_at = excluded.updated_at
                """,
                (case_id, cost_usd),
            )
            self._increment_daily_stat(conn, total_cost_usd=cost_usd)

    def get_today_stats(self) -> dict[str, float | int]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT api_calls, total_cost_usd, ng_count, review_count, match_count,
                       staleness_excluded_count, extraction_retry_count
                FROM daily_stats
                WHERE stat_date = date('now', '+9 hours')
                """
            ).fetchone()
        if row is None:
            return {
                "api_calls": 0,
                "cost": 0.0,
                "ng_count": 0,
                "review_count": 0,
                "match_count": 0,
                "staleness_excluded_count": 0,
                "extraction_retry_count": 0,
            }
        return {
            "api_calls": int(row["api_calls"]),
            "cost": float(row["total_cost_usd"]),
            "ng_count": int(row["ng_count"]),
            "review_count": int(row["review_count"]),
            "match_count": int(row["match_count"]),
            "staleness_excluded_count": int(row["staleness_excluded_count"] or 0),
            "extraction_retry_count": int(row["extraction_retry_count"] or 0),
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_cases (
                    case_id TEXT PRIMARY KEY,
                    email_subject TEXT,
                    email_date TEXT,
                    api_called INTEGER DEFAULT 0,
                    api_called_at TEXT,
                    business_status TEXT DEFAULT 'pending',
                    match_results_json TEXT,
                    total_cost_usd REAL DEFAULT 0.0,
                    prompt_version TEXT DEFAULT 'v1',
                    schema_version TEXT DEFAULT 'v1',
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now', '+9 hours')),
                    updated_at TEXT DEFAULT (datetime('now', '+9 hours'))
                )
                """
            )
            try:
                conn.execute("ALTER TABLE processed_cases ADD COLUMN retry_count INTEGER DEFAULT 0")
            except Exception:
                pass
            try:
                conn.execute(
                    "ALTER TABLE processed_cases ADD COLUMN case_last_edited_at TEXT"
                )
            except Exception:
                pass
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_stats (
                    stat_date TEXT PRIMARY KEY,
                    api_calls INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0.0,
                    ng_count INTEGER DEFAULT 0,
                    review_count INTEGER DEFAULT 0,
                    match_count INTEGER DEFAULT 0,
                    staleness_excluded_count INTEGER DEFAULT 0
                )
                """
            )
            try:
                conn.execute(
                    "ALTER TABLE daily_stats ADD COLUMN staleness_excluded_count INTEGER DEFAULT 0"
                )
            except Exception:
                pass
            try:
                conn.execute(
                    "ALTER TABLE daily_stats ADD COLUMN extraction_retry_count INTEGER DEFAULT 0"
                )
            except Exception:
                pass
            try:
                conn.execute(
                    "ALTER TABLE daily_stats ADD COLUMN oov_skip_count INTEGER DEFAULT 0"
                )
            except Exception:
                pass

    @staticmethod
    def _increment_daily_stat(
        conn: sqlite3.Connection,
        api_calls: int = 0,
        total_cost_usd: float = 0.0,
        ng_count: int = 0,
        review_count: int = 0,
        match_count: int = 0,
        staleness_excluded_count: int = 0,
        extraction_retry_count: int = 0,
        oov_skip_count: int = 0,
    ) -> None:
        conn.execute(
            """
            INSERT INTO daily_stats (
                stat_date, api_calls, total_cost_usd, ng_count, review_count, match_count,
                staleness_excluded_count, extraction_retry_count, oov_skip_count
            )
            VALUES (date('now', '+9 hours'), ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(stat_date) DO UPDATE SET
                api_calls = daily_stats.api_calls + excluded.api_calls,
                total_cost_usd = daily_stats.total_cost_usd + excluded.total_cost_usd,
                ng_count = daily_stats.ng_count + excluded.ng_count,
                review_count = daily_stats.review_count + excluded.review_count,
                match_count = daily_stats.match_count + excluded.match_count,
                staleness_excluded_count = daily_stats.staleness_excluded_count + excluded.staleness_excluded_count,
                extraction_retry_count = daily_stats.extraction_retry_count + excluded.extraction_retry_count,
                oov_skip_count = daily_stats.oov_skip_count + excluded.oov_skip_count
            """,
            (api_calls, total_cost_usd, ng_count, review_count, match_count, staleness_excluded_count, extraction_retry_count, oov_skip_count),
        )
