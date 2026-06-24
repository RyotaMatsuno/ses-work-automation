"""SQLite raw inbox storage for full email intake (Phase 1)."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import sqlite3
from pathlib import Path

_logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
RAW_INBOX_DB = BASE_DIR / "raw_inbox.db"
PROCESSED_IDS_PATH = BASE_DIR / "processed_ids.json"
PROCESSED_IDS_BAK = BASE_DIR / "processed_ids.json.bak"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS raw_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE,
    account TEXT,
    received_at TEXT,
    sender TEXT,
    subject TEXT,
    body_text TEXT,
    body_hash TEXT,
    has_attachment INTEGER DEFAULT 0,
    attachment_names TEXT,
    processed INTEGER DEFAULT 0,
    classify_result TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE VIEW IF NOT EXISTS monthly_stats AS
SELECT
  strftime('%Y-%m', received_at) as month,
  classify_result,
  COUNT(*) as count
FROM raw_emails
GROUP BY month, classify_result;
"""


def get_db_path(db_path: Path | str | None = None) -> Path:
    return Path(db_path) if db_path else RAW_INBOX_DB


def _configure_sqlite(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _configure_sqlite(conn)
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA_SQL)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(raw_emails)").fetchall()}
        if "retry_count" not in columns:
            conn.execute("ALTER TABLE raw_emails ADD COLUMN retry_count INTEGER DEFAULT 0")
        conn.commit()
    finally:
        conn.close()


def body_hash(body_text: str) -> str:
    return hashlib.sha256((body_text or "").encode("utf-8")).hexdigest()


def account_key_from_user(email_user: str) -> str:
    user_lower = (email_user or "").lower()
    if "matsuno" in user_lower:
        return "matsuno"
    if "okamoto" in user_lower:
        return "okamoto"
    return "sessales"


def insert_raw_email(
    *,
    message_id: str,
    account: str,
    received_at: str,
    sender: str,
    subject: str,
    body_text: str,
    has_attachment: bool = False,
    attachment_names: list[str] | None = None,
    db_path: Path | str | None = None,
) -> bool:
    """Insert email before LLM classification. Returns True if newly inserted."""
    if not message_id:
        return False
    init_db(db_path)
    names_json = json.dumps(attachment_names or [], ensure_ascii=False)
    digest = body_hash(body_text)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            "SELECT id FROM raw_emails WHERE message_id = ?",
            (message_id,),
        )
        if cur.fetchone():
            conn.execute(
                """
                UPDATE raw_emails
                SET account = COALESCE(NULLIF(?, ''), account),
                    received_at = COALESCE(NULLIF(?, ''), received_at),
                    sender = COALESCE(NULLIF(?, ''), sender),
                    subject = COALESCE(NULLIF(?, ''), subject),
                    body_text = COALESCE(NULLIF(?, ''), body_text),
                    body_hash = COALESCE(NULLIF(?, ''), body_hash),
                    has_attachment = CASE WHEN ? THEN 1 ELSE has_attachment END,
                    attachment_names = CASE WHEN ? != '[]' THEN ? ELSE attachment_names END
                WHERE message_id = ?
                """,
                (
                    account,
                    received_at,
                    sender,
                    subject,
                    body_text,
                    digest,
                    int(has_attachment),
                    names_json,
                    names_json,
                    message_id,
                ),
            )
            conn.commit()
            return False

        conn.execute(
            """
            INSERT INTO raw_emails (
                message_id, account, received_at, sender, subject,
                body_text, body_hash, has_attachment, attachment_names
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                account,
                received_at,
                sender,
                subject,
                body_text,
                digest,
                int(has_attachment),
                names_json,
            ),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def load_processed_ids(db_path: Path | str | None = None) -> set[str]:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT message_id FROM raw_emails WHERE processed = 1").fetchall()
        return {row["message_id"] for row in rows if row["message_id"]}
    finally:
        conn.close()


def _row_to_dict(row, queue_type: str) -> dict:
    names_raw = row["attachment_names"] or "[]"
    try:
        attachment_names = json.loads(names_raw)
    except json.JSONDecodeError:
        attachment_names = []
    if not isinstance(attachment_names, list):
        attachment_names = []
    sender = row["sender"] or ""
    return {
        "msg_id": row["message_id"],
        "subject": row["subject"] or "",
        "body": row["body_text"] or "",
        "sender": sender,
        "reply_to": sender,
        "attachments": [],
        "attachment_names": attachment_names,
        "classify_result": row["classify_result"],
        "retry_count": int(row["retry_count"] or 0),
        "_source": "db_backlog",
        "_queue_type": queue_type,
    }


def fetch_unprocessed_from_db(
    limit: int = 50,
    db_path: Path | str | None = None,
    reclass_ratio: float = 0.2,
) -> tuple[list[dict], list[dict]]:
    """DB上の processed=0 レコードを work queue として取得する。

    fresh(classify_result IS NULL) と reclass(classify_result='other') を
    比率分割で取得し、starvation を防止する。
    デフォルト: fresh 80% / reclass 20%。不足分は相互補完。
    戻り値: (fresh_items, reclass_items)
    """
    init_db(db_path)
    reclass_quota = max(1, int(limit * reclass_ratio))
    fresh_quota = limit - reclass_quota
    conn = get_connection(db_path)
    try:
        # 1. fresh (classify_result IS NULL)
        fresh_rows = conn.execute(
            """SELECT message_id, subject, body_text, sender, classify_result,
                      retry_count, attachment_names, has_attachment
               FROM raw_emails
               WHERE processed = 0 AND classify_result IS NULL
               ORDER BY id ASC LIMIT ?""",
            (fresh_quota,),
        ).fetchall()
        # 2. reclass (classify_result = 'other')
        reclass_rows = conn.execute(
            """SELECT message_id, subject, body_text, sender, classify_result,
                      retry_count, attachment_names, has_attachment
               FROM raw_emails
               WHERE processed = 0 AND classify_result = 'other'
               ORDER BY id ASC LIMIT ?""",
            (reclass_quota,),
        ).fetchall()
        # 3. 不足分補完
        total = len(fresh_rows) + len(reclass_rows)
        remain = limit - total
        if remain > 0 and len(fresh_rows) < fresh_quota:
            extra = conn.execute(
                """SELECT message_id, subject, body_text, sender, classify_result,
                          retry_count, attachment_names, has_attachment
                   FROM raw_emails
                   WHERE processed = 0 AND classify_result = 'other'
                   ORDER BY id ASC LIMIT ? OFFSET ?""",
                (remain, len(reclass_rows)),
            ).fetchall()
            reclass_rows = list(reclass_rows) + list(extra)
        elif remain > 0 and len(reclass_rows) < reclass_quota:
            extra = conn.execute(
                """SELECT message_id, subject, body_text, sender, classify_result,
                          retry_count, attachment_names, has_attachment
                   FROM raw_emails
                   WHERE processed = 0 AND classify_result IS NULL
                   ORDER BY id ASC LIMIT ? OFFSET ?""",
                (remain, len(fresh_rows)),
            ).fetchall()
            fresh_rows = list(fresh_rows) + list(extra)
        _logger.info(
            "[DEBUG] fetch_db SQL: fresh_rows=%d reclass_rows=%d",
            len(fresh_rows),
            len(reclass_rows),
        )
    finally:
        conn.close()

    fresh_items = [_row_to_dict(row, "fresh") for row in fresh_rows]
    reclass_items = [_row_to_dict(row, "reclass") for row in reclass_rows]
    return fresh_items, reclass_items


def mark_processed(
    message_id: str,
    classify_result: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    if not message_id:
        return
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO raw_emails (message_id, processed, classify_result)
            VALUES (?, 1, ?)
            ON CONFLICT(message_id) DO UPDATE SET
                processed = 1,
                classify_result = COALESCE(excluded.classify_result, raw_emails.classify_result)
            """,
            (message_id, classify_result),
        )
        conn.commit()
    finally:
        conn.close()


def update_classify_result(
    message_id: str,
    classify_result: str,
    db_path: Path | str | None = None,
) -> None:
    if not message_id:
        return
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO raw_emails (message_id, classify_result)
            VALUES (?, ?)
            ON CONFLICT(message_id) DO UPDATE SET classify_result = excluded.classify_result
            """,
            (message_id, classify_result),
        )
        conn.commit()
    finally:
        conn.close()


def get_retry_count(
    message_id: str,
    db_path: Path | str | None = None,
) -> int:
    if not message_id:
        return 0
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT retry_count FROM raw_emails WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return int(row["retry_count"]) if row and row["retry_count"] is not None else 0
    finally:
        conn.close()


def increment_retry_count(
    message_id: str,
    db_path: Path | str | None = None,
) -> int:
    """Notion登録失敗時に retry_count を +1 して新しい値を返す。"""
    if not message_id:
        return 0
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO raw_emails (message_id, retry_count)
            VALUES (?, 1)
            ON CONFLICT(message_id) DO UPDATE SET
                retry_count = COALESCE(raw_emails.retry_count, 0) + 1
            """,
            (message_id,),
        )
        conn.commit()
        row = conn.execute(
            "SELECT retry_count FROM raw_emails WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return int(row["retry_count"]) if row and row["retry_count"] is not None else 1
    finally:
        conn.close()


def migrate_processed_ids_json(
    processed_path: Path | str | None = None,
    db_path: Path | str | None = None,
    backup_path: Path | str | None = None,
) -> int:
    """Migrate processed_ids.json into SQLite and rename source to .bak."""
    src = Path(processed_path) if processed_path else PROCESSED_IDS_PATH
    bak = Path(backup_path) if backup_path else PROCESSED_IDS_BAK
    if not src.exists():
        return 0

    init_db(db_path)
    with open(src, encoding="utf-8") as f:
        ids = json.load(f)
    if not isinstance(ids, list):
        raise ValueError("processed_ids.jsonの形式がlistではありません")

    conn = get_connection(db_path)
    inserted = 0
    try:
        for msg_id in ids:
            if not msg_id:
                continue
            cur = conn.execute(
                "SELECT id, processed FROM raw_emails WHERE message_id = ?",
                (msg_id,),
            )
            row = cur.fetchone()
            if row:
                if not row["processed"]:
                    conn.execute(
                        "UPDATE raw_emails SET processed = 1, classify_result = COALESCE(classify_result, 'migrated') WHERE message_id = ?",
                        (msg_id,),
                    )
            else:
                conn.execute(
                    """
                    INSERT INTO raw_emails (message_id, processed, classify_result)
                    VALUES (?, 1, 'migrated')
                    """,
                    (msg_id,),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()

    if bak.exists():
        bak.unlink()
    shutil.move(str(src), str(bak))
    return inserted


def count_rows(db_path: Path | str | None = None) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM raw_emails").fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()


def count_processed(db_path: Path | str | None = None) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM raw_emails WHERE processed = 1").fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()


def count_unprocessed(db_path: Path | str | None = None) -> int:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        row = conn.execute("SELECT COUNT(*) AS c FROM raw_emails WHERE processed = 0").fetchone()
        return int(row["c"]) if row else 0
    finally:
        conn.close()


def monthly_stats_rows(db_path: Path | str | None = None) -> list[dict]:
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        rows = conn.execute("SELECT month, classify_result, count FROM monthly_stats").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def reset_other_for_reclassify(db_path: Path | str | None = None) -> int:
    """other判定かつ件名に案件キーワードを含むレコードのprocessed=0にリセット。"""
    init_db(db_path)
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            UPDATE raw_emails
            SET processed = 0, retry_count = 0
            WHERE classify_result = 'other'
              AND (
                subject LIKE '%案件%'
                OR subject LIKE '%募集%'
                OR subject LIKE '%常駐%'
                OR subject LIKE '%万円%'
                OR subject LIKE '%万〜%'
                OR subject LIKE '%面談%'
                OR subject LIKE '%決済者直%'
                OR subject LIKE '%フルリモート%'
              )
            """
        )
        conn.commit()
        return int(cur.rowcount)
    finally:
        conn.close()