from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from common.io_utils import setup_stdout
from common.ledger import _release_dedup_in_tx

setup_stdout()

# dedup_claims.error 列の意味（SPEC v2.10.1 §3.2）:
#   0 = success 確定
#   1 = permanent failure 確定
#   2 = released(transient): release_dedup で完了マーキング

BASE_DIR = Path(__file__).resolve().parent.parent
_DEDUP_TARGET_PATH = BASE_DIR / "config" / "dedup_target_required.json"

_dedup_target_map: dict | None = None


def _load_dedup_target() -> dict:
    global _dedup_target_map
    if _dedup_target_map is None:
        try:
            _dedup_target_map = json.loads(_DEDUP_TARGET_PATH.read_text(encoding="utf-8"))
        except Exception:
            _dedup_target_map = {}
    return _dedup_target_map


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    from common.state_store import init_schema, open_conn

    init_schema()
    return open_conn()


def compose_dedup_key(date: str, block_type: str, phase: str, target_id: str = "") -> str:
    """SPEC §5.1: dedup_key = f"{date}:{block_type}:{phase}:{target_id}" """
    return f"{date}:{block_type}:{phase}:{target_id}"


def validate_target_id(block_type: str, target_id: str) -> None:
    """target_id 必須チェック（SPEC §5.4）。必須なのに未指定なら ValueError を raise する。"""
    spec = _load_dedup_target().get(block_type, {})
    if spec.get("target_id") == "required" and not target_id:
        raise ValueError(f"target_id required for block_type={block_type}")


def claim_dedup(dedup_key: str, ttl_sec: int = 3600) -> str | None:
    """事前 claim。UNIQUE 違反時は None を返す（SPEC §5.2）。
    同一トランザクション内で期限切れ未確定 claim を inline purge する（SPEC §5.3）。
    """
    claim_id = str(uuid.uuid4())
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            # inline purge: 期限切れ未確定 claim を削除（SPEC §5.3）
            conn.execute(
                "DELETE FROM dedup_claims"
                " WHERE confirmed=0"
                "   AND first_seen <= datetime('now', '-' || ttl_sec || ' seconds')"
            )
            # released(transient) 済み claim を除去して同一 dedup_key の再 claim を可能にする
            conn.execute(
                "DELETE FROM dedup_claims WHERE dedup_key=? AND confirmed=1 AND error=2",
                (dedup_key,),
            )
            # 新規 claim INSERT
            conn.execute(
                "INSERT OR FAIL INTO dedup_claims"
                "(claim_id, dedup_key, first_seen, ttl_sec, confirmed, error)"
                " VALUES(?,?,datetime('now'),?,0,0)",
                (claim_id, dedup_key, ttl_sec),
            )
            conn.execute("COMMIT")
        except sqlite3.IntegrityError:
            conn.execute("ROLLBACK")
            return None
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    return claim_id


def release_dedup(claim_id: str) -> None:
    """transient失敗時: confirmed=1, error=2 マーカーをセットする（SPEC v2.10.1 §3.1）。"""
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _release_dedup_in_tx(conn, claim_id)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def confirm_dedup(claim_id: str, error: bool = False) -> None:
    """成功/permanent失敗時: dedup_claims.confirmed=1 をセットする（SPEC §5.2）。"""
    from common.ledger import _confirm_dedup_in_tx

    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _confirm_dedup_in_tx(conn, claim_id, error=error)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def archive_confirmed_dedup_claims(conn: sqlite3.Connection | None = None) -> int:
    """confirmed=1 AND error IN (0,1) の claim を archive へ移動する（error=2 はスキップ、§3.3）。"""
    own_conn = conn is None
    if own_conn:
        conn = _get_conn()
    try:
        if own_conn:
            conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            "SELECT claim_id, dedup_key, error FROM dedup_claims WHERE confirmed=1 AND error IN (0, 1)"
        ).fetchall()
        archived = 0
        for row in rows:
            conn.execute(
                "INSERT OR IGNORE INTO dedup_claims_archive(claim_id, dedup_key, archived_at, error)"
                " VALUES(?,?,datetime('now'),?)",
                (row["claim_id"], row["dedup_key"], row["error"]),
            )
            conn.execute("DELETE FROM dedup_claims WHERE claim_id=?", (row["claim_id"],))
            archived += 1
        if own_conn:
            conn.execute("COMMIT")
        return archived
    except Exception:
        if own_conn:
            conn.execute("ROLLBACK")
        raise
    finally:
        if own_conn:
            conn.close()
