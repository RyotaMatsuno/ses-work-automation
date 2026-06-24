from __future__ import annotations

import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common.io_utils import setup_stdout

setup_stdout()


class StateMismatchError(Exception):
    """finalize の事前整合チェックで不整合検出時に内部的に raise する。"""


@dataclass
class FinalizeState:
    reservation_exists: bool
    reservation_finalized: bool
    claim_exists: bool
    claim_confirmed: bool


BASE_DIR = Path(__file__).resolve().parent.parent
COST_LOG = BASE_DIR / "usage_tracker" / "cost_log.jsonl"
ENV_PATH = BASE_DIR / "config" / ".env"
JST = timezone(timedelta(hours=9))

try:
    from dotenv import dotenv_values as _dotenv_values

    _ENV: dict = _dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}
except ImportError:
    _ENV = {}


def _get_env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _ENV.get(name, default)


def _float_env(name: str, default: float) -> float:
    try:
        return float(_get_env(name, "") or default)
    except (TypeError, ValueError):
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(_get_env(name, "") or default)
    except (TypeError, ValueError):
        return default


# グローバル上限（SPEC §7, §13）
DAILY_HARD_USD = _float_env("COST_GUARD_DAILY_USD", 8.0)
MONTHLY_USD = _float_env("COST_GUARD_MONTHLY_USD", 140.0)

MODEL_RATES_PATH = BASE_DIR / "config" / "model_rates.json"
_model_rates: dict | None = None


def _load_model_rates() -> dict:
    global _model_rates
    if _model_rates is None:
        try:
            _model_rates = json.loads(MODEL_RATES_PATH.read_text(encoding="utf-8"))
        except Exception:
            _model_rates = {}
    return _model_rates


def _estimate(in_tokens: int, out_tokens: int, model: str) -> float:
    """モデルとトークン数からコストを推定する（USD）。"""
    rates = _load_model_rates()
    model_key = (model or "").lower()

    # 完全一致
    rate = rates.get(model or "")
    if rate is None:
        # 部分一致
        for k, v in rates.items():
            if k.lower() in model_key or model_key in k.lower():
                rate = v
                break

    if rate is None:
        # gpt-4o の1.5倍（保守的 fallback rate、SPEC §4.1）
        gpt4o = rates.get("gpt-4o", {"input": 2.5, "output": 10.0})
        rate = {"input": gpt4o["input"] * 1.5, "output": gpt4o["output"] * 1.5}

    return in_tokens * rate["input"] / 1_000_000 + out_tokens * rate["output"] / 1_000_000


def _today_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d")


def _month_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m")


def _now_date() -> str:
    return _today_jst()


def _now_month() -> str:
    return _month_jst()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_conn() -> sqlite3.Connection:
    from common.state_store import init_schema, open_conn

    init_schema()
    return open_conn()


def _append_log(entry: dict) -> None:
    try:
        COST_LOG.parent.mkdir(parents=True, exist_ok=True)
        with COST_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _call_limit(phase: str) -> int:
    """フェーズ別の日次呼び出し上限（SPEC §3.2.2）。"""
    per_phase = _int_env(f"DAILY_CALL_LIMIT_{phase.upper()}", 0)
    if per_phase > 0:
        return per_phase
    if phase in ("matching_batch", "matching_pipeline"):
        legacy = _int_env("DAILY_CALL_LIMIT_MATCHING", 0)
        if legacy > 0:
            return legacy
    return _int_env("DAILY_CALL_LIMIT_DEFAULT", 30)


# ──────────────────────────────────────────────
# 既存関数（後方互換保証、シグネチャ温存）
# ──────────────────────────────────────────────


def can_spend(est_in: int = 200, est_out: int = 300, model: str = "") -> bool:
    """API呼び出し前に確認。Falseならスキップすること。

    DB読み取り失敗時は例外を送出する。cost_guard.allowed() が fail-close でブロックする。
    """
    est = _estimate(est_in, est_out, model)
    conn = _get_conn()
    try:
        today = _now_date()
        month = _now_month()
        row = conn.execute("SELECT daily_usd FROM daily_state WHERE date=?", (today,)).fetchone()
        daily_usd = row["daily_usd"] if row else 0.0
        row2 = conn.execute("SELECT monthly_usd FROM monthly_state WHERE month=?", (month,)).fetchone()
        monthly_usd = row2["monthly_usd"] if row2 else 0.0
    finally:
        conn.close()

    if daily_usd + est > DAILY_HARD_USD:
        _append_log(
            {
                "ts": _now_iso(),
                "script": "cost_guard",
                "model": model,
                "input_tokens": est_in,
                "output_tokens": est_out,
                "cost_usd": est,
                "blocked": True,
                "reason": "daily_limit",
            }
        )
        return False
    if monthly_usd + est > MONTHLY_USD:
        _append_log(
            {
                "ts": _now_iso(),
                "script": "cost_guard",
                "model": model,
                "input_tokens": est_in,
                "output_tokens": est_out,
                "cost_usd": est,
                "blocked": True,
                "reason": "monthly_limit",
            }
        )
        return False
    return True


def record(
    in_tokens: int,
    out_tokens: int,
    model: str,
    script: str,
    *,
    phase: str | None = None,
    reservation_id: str | None = None,
    fallback: bool = False,
    unknown_model: bool = False,
    error: bool = False,
    reason: str | None = None,
    detail: str | None = None,
) -> None:
    """API呼び出し成功後に必ず呼ぶ。コストを記録する（SPEC §11.2）。"""
    cost = _estimate(in_tokens, out_tokens, model)
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _record_in_tx(
                conn,
                in_tokens,
                out_tokens,
                model,
                script,
                phase=phase,
                reservation_id=reservation_id,
                fallback=fallback,
                unknown_model=unknown_model,
                error=error,
                reason=reason,
                detail=detail,
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    _append_log(
        {
            "ts": _now_iso(),
            "script": script,
            "model": model,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "cost_usd": cost,
            "error": error,
            **({"reason": reason} if reason else {}),
            **({"fallback": True} if fallback else {}),
            **({"unknown_model": True} if unknown_model else {}),
        }
    )


def daily_total() -> float:
    """今日の累計コスト（USD）。"""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT daily_usd FROM daily_state WHERE date=?", (_now_date(),)).fetchone()
        return row["daily_usd"] if row else 0.0
    finally:
        conn.close()


def monthly_total() -> float:
    """今月の累計コスト（USD）。"""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT monthly_usd FROM monthly_state WHERE month=?", (_now_month(),)).fetchone()
        return row["monthly_usd"] if row else 0.0
    finally:
        conn.close()


# ──────────────────────────────────────────────
# pending_queue 管理（DAILY_CALL_LIMIT 超過時の保留キュー）
# ──────────────────────────────────────────────


def enqueue_pending(
    phase: str,
    *,
    block_type: str = "",
    target_id: str = "",
    script: str = "",
) -> int:
    """DAILY_CALL_LIMIT 超過時の処理を pending_queue に追加する。戻り値は行ID。"""
    from common.state_store import begin_immediate

    with begin_immediate() as conn:
        cur = conn.execute(
            "INSERT INTO pending_queue(phase, block_type, target_id, script, queued_at) VALUES(?,?,?,?,?)",
            (phase, block_type, target_id, script, _now_iso()),
        )
        return cur.lastrowid


def fetch_pending_queue(phase: str | None = None, limit: int = 100) -> list[dict]:
    """status='pending' のエントリを FIFO（id 昇順）で返す。"""
    conn = _get_conn()
    try:
        if phase:
            rows = conn.execute(
                "SELECT id, phase, block_type, target_id, script, queued_at FROM pending_queue"
                " WHERE status='pending' AND phase=? ORDER BY id LIMIT ?",
                (phase, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, phase, block_type, target_id, script, queued_at FROM pending_queue"
                " WHERE status='pending' ORDER BY id LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def mark_pending_done(queue_id: int) -> None:
    """pending_queue エントリを処理済みに更新する。"""
    from common.state_store import begin_immediate

    with begin_immediate() as conn:
        conn.execute("UPDATE pending_queue SET status='done' WHERE id=?", (queue_id,))


def expire_old_pending(days: int = 7) -> int:
    """days 日超の pending エントリを失効させる。失効件数を返す。"""
    from common.state_store import begin_immediate

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with begin_immediate() as conn:
        cur = conn.execute(
            "UPDATE pending_queue SET status='expired' WHERE status='pending' AND queued_at < ?",
            (cutoff,),
        )
        return cur.rowcount


def count_pending_queue(phase: str | None = None) -> int:
    """status='pending' の件数を返す。"""
    conn = _get_conn()
    try:
        if phase:
            row = conn.execute(
                "SELECT COUNT(*) FROM pending_queue WHERE status='pending' AND phase=?", (phase,)
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM pending_queue WHERE status='pending'").fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def has_pending_target(phase: str, target_id: str) -> bool:
    """同一 target_id が既に pending かどうか。"""
    if not target_id:
        return False
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM pending_queue WHERE status='pending' AND phase=? AND target_id=? LIMIT 1",
            (phase, target_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 新規関数（SPEC §11.3）
# ──────────────────────────────────────────────

RESERVATION_TTL_SEC = int(os.environ.get("RESERVATION_TTL_SEC", "600"))


def cleanup_stale_reservations(ttl_sec: int | None = None) -> int:
    """Release orphaned reservations older than ttl_sec (default 10 minutes)."""
    ttl = RESERVATION_TTL_SEC if ttl_sec is None else ttl_sec
    conn = _get_conn()
    released = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        rows = conn.execute(
            """
            SELECT reservation_id FROM reservations
            WHERE finalized=0
              AND created_at <= datetime('now', ?)
            """,
            (f"-{ttl} seconds",),
        ).fetchall()
        for row in rows:
            try:
                _release_in_tx(conn, row["reservation_id"])
                released += 1
            except StateMismatchError:
                pass
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return released


def reserve(
    phase: str,
    *,
    block_type: str = "",
    target_id: str = "",
    script: str = "",
) -> str | None:
    """DAILY_CALL_LIMIT を予約方式で確認・予約する（SPEC §3.2）。
    予約成功時: reservation_id (str) を返す。
    上限超過時: pending_queue にエントリを追加して None を返す。
    """
    if not phase:
        raise ValueError("phase is required")
    cleanup_stale_reservations()
    today = _now_date()
    limit = _call_limit(phase)
    reservation_id = str(uuid.uuid4())
    conn = _get_conn()
    over_limit = False
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT reserved, consumed FROM phase_calls WHERE date=? AND phase=?", (today, phase)
            ).fetchone()
            reserved = row["reserved"] if row else 0
            consumed = row["consumed"] if row else 0
            if consumed + reserved >= limit:
                conn.execute("ROLLBACK")
                over_limit = True
            else:
                if row:
                    conn.execute("UPDATE phase_calls SET reserved=reserved+1 WHERE date=? AND phase=?", (today, phase))
                else:
                    conn.execute("INSERT INTO phase_calls(date, phase, reserved, consumed) VALUES(?,?,1,0)", (today, phase))
                conn.execute(
                    "INSERT INTO reservations(reservation_id, date, phase, created_at, finalized) VALUES(?,?,?,?,0)",
                    (reservation_id, today, phase, _now_iso()),
                )
                conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()

    if over_limit:
        try:
            enqueue_pending(phase, block_type=block_type, target_id=target_id, script=script)
        except Exception:
            pass
        return None
    return reservation_id


def release(reservation_id: str) -> None:
    """transient失敗時に予約を解放する（consumed は加算しない、SPEC §3.2.1）。"""
    if not reservation_id:
        raise ValueError("reservation_id is required")
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _release_in_tx(conn, reservation_id)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()


def check_daily_limit(phase: str) -> bool:
    """現在の日次呼び出し数が上限未満か確認する（監視・モニタリング用のみ）。
    本番判定では reserve() を使うこと。
    """
    today = _now_date()
    limit = _call_limit(phase)
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT reserved, consumed FROM phase_calls WHERE date=? AND phase=?", (today, phase)
        ).fetchone()
        if not row:
            return True
        return (row["reserved"] + row["consumed"]) < limit
    finally:
        conn.close()


def _log_event_in_tx(
    conn: sqlite3.Connection,
    reason: str,
    detail: str = "",
    phase: str = "",
    block_type: str = "",
    script: str = "",
) -> None:
    """tx 内文脈専用。外側 conn をそのまま使い、新たに BEGIN を取らない（SPEC v2.10.1 §5.1）。"""
    conn.execute(
        "INSERT INTO event_log(timestamp, reason, detail, phase, block_type, script) VALUES(?,?,?,?,?,?)",
        (_now_iso(), reason, detail, phase, block_type, script),
    )


def log_event(
    reason: str,
    detail: str = "",
    phase: str = "",
    block_type: str = "",
    script: str = "",
) -> None:
    """非 tx 文脈専用。自前で BEGIN IMMEDIATE を取得する（SPEC v2.10.1 §5.2）。"""
    from common.state_store import begin_immediate

    with begin_immediate() as conn:
        _log_event_in_tx(conn, reason, detail, phase, block_type, script)


def _load_finalize_state_in_tx(
    conn: sqlite3.Connection,
    reservation_id: str | None,
    claim_id: str | None,
) -> FinalizeState:
    """tx 内で reservation/claim の状態をスナップショット取得する（SPEC v2.10.1 §2）。"""
    res_row = None
    if reservation_id:
        res_row = conn.execute(
            "SELECT finalized FROM reservations WHERE reservation_id=?",
            (reservation_id,),
        ).fetchone()
    res_exists = res_row is not None
    res_finalized = res_exists and res_row["finalized"] == 1

    if claim_id is None:
        return FinalizeState(
            reservation_exists=res_exists,
            reservation_finalized=res_finalized,
            claim_exists=True,
            claim_confirmed=True,
        )

    claim_row = conn.execute(
        "SELECT confirmed FROM dedup_claims WHERE claim_id=?",
        (claim_id,),
    ).fetchone()
    claim_exists = claim_row is not None
    claim_confirmed = claim_exists and claim_row["confirmed"] != 0

    return FinalizeState(
        reservation_exists=res_exists,
        reservation_finalized=res_finalized,
        claim_exists=claim_exists,
        claim_confirmed=claim_confirmed,
    )


def estimate_cause(state: dict) -> str:
    """停止理由を人間可読な文字列で返す（SPEC §11.3）。"""
    reason = state.get("reason", "")
    detail = state.get("detail", "")

    if reason == "error_internal":
        if detail == "lock_timeout":
            return "internal error: lock_timeout (sqlite BEGIN IMMEDIATE timeout=5s)"
        if detail == "finalize_state_mismatch" or detail.startswith("finalize_state_mismatch:"):
            return "internal error: finalize_state_mismatch (transaction rolled back)"
        return f"internal error: {detail}"

    if reason == "stopped_budget":
        daily = state.get("daily_usd", "?")
        monthly = state.get("monthly_usd", "?")
        dl = state.get("daily_limit", DAILY_HARD_USD)
        ml = state.get("monthly_limit", MONTHLY_USD)
        if isinstance(daily, float) and daily >= dl:
            return f"daily_usd ${daily:.2f} > ${dl} (DAILY_HARD_USD)"
        return f"monthly_usd ${monthly:.2f} > ${ml} (MONTHLY_USD)"

    if reason == "stopped_call_limit":
        phase = state.get("phase", "?")
        return f"DAILY_CALL_LIMIT exceeded for phase={phase}"

    if reason == "stopped_phase_threshold":
        cls = state.get("model_class", "?")
        cost = state.get("estimated_cost", "?")
        thr = state.get("threshold", "?")
        return f"phase threshold exceeded: ${cost} > ${thr} (class={cls})"

    return reason


# ──────────────────────────────────────────────
# 内部 _in_tx 関数（finalize() から単一トランザクションで使用、SPEC §3.2.2）
# ──────────────────────────────────────────────


def _record_in_tx(
    conn: sqlite3.Connection,
    in_tokens: int,
    out_tokens: int,
    model: str,
    script: str,
    *,
    phase: str | None = None,
    reservation_id: str | None = None,
    fallback: bool = False,
    unknown_model: bool = False,
    error: bool = False,
    reason: str | None = None,
    detail: str | None = None,
) -> None:
    """BEGIN IMMEDIATE 内で呼ぶ。外側でトランザクションを開始すること。"""
    if reservation_id:
        res_row = conn.execute(
            "SELECT finalized FROM reservations WHERE reservation_id=?",
            (reservation_id,),
        ).fetchone()
        if res_row is None:
            raise StateMismatchError(f"reservation not found: {reservation_id}")
        if res_row["finalized"] == 1:
            raise StateMismatchError(f"reservation already finalized: {reservation_id}")

    cost = _estimate(in_tokens, out_tokens, model)
    today = _now_date()
    month = _now_month()

    # daily_state UPSERT
    conn.execute(
        "INSERT INTO daily_state(date, daily_usd, daily_calls) VALUES(?,?,1)"
        " ON CONFLICT(date) DO UPDATE SET"
        "   daily_usd=daily_usd+excluded.daily_usd,"
        "   daily_calls=daily_calls+1",
        (today, cost),
    )
    # monthly_state UPSERT
    conn.execute(
        "INSERT INTO monthly_state(month, monthly_usd) VALUES(?,?)"
        " ON CONFLICT(month) DO UPDATE SET monthly_usd=monthly_usd+excluded.monthly_usd",
        (month, cost),
    )
    # 予約確定
    if reservation_id:
        conn.execute(
            "UPDATE phase_calls SET reserved=MAX(0,reserved-1), consumed=consumed+1"
            " WHERE date=? AND phase=("
            "  SELECT phase FROM reservations WHERE reservation_id=?)",
            (today, reservation_id),
        )
        conn.execute("UPDATE reservations SET finalized=1 WHERE reservation_id=?", (reservation_id,))


def _release_in_tx(conn: sqlite3.Connection, reservation_id: str) -> None:
    """BEGIN IMMEDIATE 内で呼ぶ。reserved -= 1、consumed は加算しない（SPEC §3.2.1）。"""
    row = conn.execute(
        "SELECT date, phase, finalized FROM reservations WHERE reservation_id=?", (reservation_id,)
    ).fetchone()
    if row is None:
        raise StateMismatchError(f"reservation not found in release: {reservation_id}")
    if row["finalized"] == 1:
        raise StateMismatchError(f"reservation already finalized: {reservation_id}")
    conn.execute(
        "UPDATE phase_calls SET reserved=MAX(0,reserved-1) WHERE date=? AND phase=?", (row["date"], row["phase"])
    )
    conn.execute("UPDATE reservations SET finalized=1 WHERE reservation_id=?", (reservation_id,))


def _confirm_dedup_in_tx(conn: sqlite3.Connection, claim_id: str, error: bool = False) -> None:
    """BEGIN IMMEDIATE 内で呼ぶ。dedup_claims.confirmed=1 をセットする。"""
    row = conn.execute("SELECT confirmed FROM dedup_claims WHERE claim_id=?", (claim_id,)).fetchone()
    if row is None:
        raise StateMismatchError(f"claim not found: {claim_id}")
    if row["confirmed"] != 0:
        raise StateMismatchError(f"claim already finalized: {claim_id}")
    conn.execute("UPDATE dedup_claims SET confirmed=1, error=? WHERE claim_id=?", (1 if error else 0, claim_id))


def _release_dedup_in_tx(conn: sqlite3.Connection, claim_id: str) -> None:
    """BEGIN IMMEDIATE 内で呼ぶ。transient release: confirmed=1, error=2 マーカー（SPEC v2.10.1 §3.1）。"""
    row = conn.execute("SELECT confirmed FROM dedup_claims WHERE claim_id=?", (claim_id,)).fetchone()
    if row is None:
        raise StateMismatchError(f"claim not found in release: {claim_id}")
    if row["confirmed"] != 0:
        raise StateMismatchError(f"claim already finalized: {claim_id}")
    conn.execute(
        "UPDATE dedup_claims SET confirmed=1, error=2 WHERE claim_id=?",
        (claim_id,),
    )


# ──────────────────────────────────────────────
# Re-exports from dedup (SPEC §11.3)
# ──────────────────────────────────────────────


def claim_dedup(dedup_key: str, ttl_sec: int = 3600) -> str | None:
    from common.dedup import claim_dedup as _claim

    return _claim(dedup_key, ttl_sec)


def release_dedup(claim_id: str) -> None:
    from common.dedup import release_dedup as _release

    _release(claim_id)


def confirm_dedup(claim_id: str, error: bool = False) -> None:
    from common.dedup import confirm_dedup as _confirm

    _confirm(claim_id, error)
