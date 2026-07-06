# -*- coding: utf-8 -*-
"""
cost_guard.py - API cost guard for all active LLM routes.

usage_tracker/cost_log.jsonl をグローバル合算で監視し、上限超過時に
WindowsタスクとCloud RunのLLM経路を停止する。

v2: Decision dataclass + allowed() / finalize() 統一エントリポイントを追加（SPEC v2.10）
"""

from __future__ import annotations

import json
import os
import subprocess
import sys as _sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Tuple

_BASE_DIR = Path(__file__).resolve().parent
if str(_BASE_DIR) not in _sys.path:
    _sys.path.insert(0, str(_BASE_DIR))

try:
    from common.io_utils import setup_stdout

    setup_stdout()
except Exception:
    pass


# 2026-06-12: 多層防御設計に変更
# レイヤー1 (common/ledger.py): 通常運用上限 $8/日・$140/月（.envから読む）
# レイヤー2 (cost_guard.py)   : 緊急停止ライン $20/日・$300/月（レイヤー1が破壊された場合の最終砦）
# SOFT_DAILY_LIMITは早期警告用（$8の50%）
SOFT_DAILY_LIMIT = 4.0  # ソフト警告：日次$4 (レイヤー1上限の50%)
HARD_DAILY_LIMIT = 20.0  # 緊急停止：日次$20 (Cloud Run LLM_KILL=1発動ライン)
MONTHLY_LIMIT = 300.0  # 月次緊急停止：$300 (レイヤー1月次$140の約2倍が最終砦)
COST_LOG = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")
STATE_FILE = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cost_guard_state.json")
LINE_USER_ID = "Ue3508b43b84991f5a68281da5bf4cf39"
JST = timezone(timedelta(hours=9))

ACTIVE_TASKS = [
    "SES_MailPipeline",
    "SES_MatchingV3",
    "jobz_importer",
    "SES_Outlook_9h",
    "SES_Outlook_13h",
    "SES_Outlook_18h",
    "jobz_daily_report",  # 追加: 日次レポート
    "freee_auto_invoice",  # 追加: freee請求書
    "freee_invoice_send",  # 追加: freee送付
]


def default_state(now: datetime) -> Dict[str, Any]:
    return {
        "stopped_today": False,
        "stopped_monthly": False,
        "soft_alerted_today": False,
        "last_date": now.strftime("%Y-%m-%d"),
        "last_month": now.strftime("%Y-%m"),
    }


def load_state(now: datetime) -> Dict[str, Any]:
    state = default_state(now)
    if not STATE_FILE.exists():
        return state

    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            state.update(loaded)
    except Exception as e:
        print(f"[state error] load failed: {e}")

    return reset_state_if_needed(state, now)


def reset_state_if_needed(state: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    today = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")

    if state.get("last_date") != today:
        state["stopped_today"] = False
        state["soft_alerted_today"] = False
        state["last_date"] = today

    if state.get("last_month") != month:
        state["stopped_monthly"] = False
        state["last_month"] = month

    return state


def save_state(state: Dict[str, Any]) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[state error] save failed: {e}")


def parse_timestamp(value: Any) -> datetime:
    if not value:
        raise ValueError("empty timestamp")

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    ts = datetime.fromisoformat(text)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=JST)
    return ts.astimezone(JST)


def get_costs() -> Tuple[float, float, float]:
    now = datetime.now(JST)
    hour_start = now - timedelta(hours=1)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    hourly = 0.0
    daily = 0.0
    monthly = 0.0

    try:
        if not COST_LOG.exists():
            print(f"[cost log] not found: {COST_LOG}")
            return hourly, daily, monthly

        with COST_LOG.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                    ts = parse_timestamp(record.get("ts"))
                    cost = float(record.get("cost_usd", 0) or 0)
                except Exception:
                    continue

                if ts >= hour_start:
                    hourly += cost
                if ts >= day_start:
                    daily += cost
                if ts >= month_start:
                    monthly += cost
    except Exception as e:
        print(f"[cost error] {e}")
        return 0.0, 0.0, 0.0

    # ledger (common/cost_state.json) を正とし monthly を上書き
    try:
        import sys as _sys

        _ses = str(Path(__file__).resolve().parent)
        if _ses not in _sys.path:
            _sys.path.insert(0, _ses)
        from common.ledger import daily_total as _ledger_daily
        from common.ledger import monthly_total as _ledger_monthly

        _lm = _ledger_monthly()
        _ld = _ledger_daily()
        monthly = max(monthly, _lm)
        daily = max(daily, _ld)
    except Exception:
        pass
    return hourly, daily, monthly


def run_task_change(task_name: str, action: str) -> None:
    result = subprocess.run(
        ["schtasks", "/Change", "/TN", task_name, action],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    print(f"[task] {task_name} {action}: returncode={result.returncode}")
    if stdout:
        print(f"[task stdout] {stdout}")
    if stderr:
        print(f"[task stderr] {stderr}")


def update_cloud_run(llm_kill: int) -> None:
    try:
        result = subprocess.run(
            [
                "gcloud",
                "run",
                "services",
                "update",
                "line-webhook",
                "--region",
                "asia-northeast1",
                "--update-env-vars",
                f"LLM_KILL={llm_kill}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        print(f"[cloud run] LLM_KILL={llm_kill}: returncode={result.returncode}")
        if stdout:
            print(f"[cloud run stdout] {stdout[:500]}")
        if stderr:
            print(f"[cloud run stderr] {stderr[:500]}")
    except Exception as e:
        print(f"[cloud run error] LLM_KILL={llm_kill}: {e}")


def disable_tasks() -> None:
    for task_name in ACTIVE_TASKS:
        run_task_change(task_name, "/DISABLE")
    update_cloud_run(1)


def enable_tasks() -> None:
    for task_name in ACTIVE_TASKS:
        run_task_change(task_name, "/ENABLE")
    update_cloud_run(0)


def send_line(message: str) -> None:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        print(f"[LINE skip] LINE_CHANNEL_ACCESS_TOKEN is not set: {message}")
        return

    body = json.dumps(
        {
            "to": LINE_USER_ID,
            "messages": [{"type": "text", "text": message}],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.line.me/v2/bot/message/push",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(f"[LINE sent] status={response.status}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        print(f"[LINE error] status={e.code} body={detail}")
    except Exception as e:
        print(f"[LINE error] {e}")


def main() -> None:
    now = datetime.now(JST)
    state = load_state(now)
    hourly, daily, monthly = get_costs()

    print(
        f"[cost] hourly=${hourly:.4f} daily=${daily:.4f} monthly=${monthly:.4f} "
        f"date={now.strftime('%Y-%m-%d')} month={now.strftime('%Y-%m')}"
    )

    if monthly >= MONTHLY_LIMIT and not state.get("stopped_monthly", False):
        disable_tasks()
        message = (
            "APIコスト月次上限到達（全停止）\n"
            f"月次: ${monthly:.2f} / 上限 ${MONTHLY_LIMIT:.2f}\n"
            "SES全タスク + Cloud Runを停止しました"
        )
        print(f"[ALERT-MONTHLY] {message}")
        send_line(message)
        state["stopped_monthly"] = True

    elif daily >= HARD_DAILY_LIMIT and not state.get("stopped_today", False):
        disable_tasks()
        message = (
            "APIコスト日次上限到達（全停止）\n"
            f"日次: ${daily:.2f} / 上限 ${HARD_DAILY_LIMIT:.2f}\n"
            "SES全タスク + Cloud Runを停止しました"
        )
        print(f"[ALERT-DAILY-HARD] {message}")
        send_line(message)
        state["stopped_today"] = True

    elif daily >= SOFT_DAILY_LIMIT and not state.get("soft_alerted_today", False):
        message = f"APIコスト日次警告\n日次: ${daily:.2f} / 警告 ${SOFT_DAILY_LIMIT:.2f}\n自動停止はしていません"
        print(f"[WARN-DAILY-SOFT] {message}")
        send_line(message)
        state["soft_alerted_today"] = True

    elif daily < SOFT_DAILY_LIMIT and state.get("stopped_today", False):
        enable_tasks()
        message = (
            "APIコスト日次復旧\n"
            f"日次: ${daily:.2f} / 警告 ${SOFT_DAILY_LIMIT:.2f}\n"
            "SES全タスク + Cloud Runを再起動しました"
        )
        print(f"[RECOVERY-DAILY] {message}")
        send_line(message)
        state["stopped_today"] = False

    else:
        print("[cost] no action")

    save_state(state)


if __name__ == "__main__":
    main()


# ══════════════════════════════════════════════════════════════════════════════
# cost_guard v2 統一エントリポイント（SPEC v2.10）
# ══════════════════════════════════════════════════════════════════════════════

_ENV_PATH = _BASE_DIR / "config" / ".env"
try:
    from dotenv import dotenv_values as _dotenv_values

    _CG_ENV: dict = _dotenv_values(_ENV_PATH, encoding="utf-8") if _ENV_PATH.exists() else {}
except ImportError:
    _CG_ENV = {}


def _cg_env(name: str, default: str = "") -> str:
    return os.environ.get(name) or _CG_ENV.get(name, default)


def _cg_float(name: str, default: float) -> float:
    try:
        return float(_cg_env(name) or default)
    except (TypeError, ValueError):
        return default


_MODEL_RATES_PATH = _BASE_DIR / "config" / "model_rates.json"
_model_rates_cache: dict | None = None


def _load_rates() -> dict:
    global _model_rates_cache
    if _model_rates_cache is None:
        try:
            _model_rates_cache = json.loads(_MODEL_RATES_PATH.read_text(encoding="utf-8"))
        except Exception:
            _model_rates_cache = {}
    return _model_rates_cache


def _estimate_cost(model: str, in_tokens: int, out_tokens: int) -> float:
    rates = _load_rates()
    rate = rates.get(model)
    if rate is None:
        gpt4o = rates.get("gpt-4o", {"input": 2.5, "output": 10.0})
        rate = {"input": gpt4o["input"] * 1.5, "output": gpt4o["output"] * 1.5}
    return in_tokens * rate["input"] / 1_000_000 + out_tokens * rate["output"] / 1_000_000


class Reasons(str, Enum):
    """SPEC §9 reason enum 14値。"""

    ok = "ok"
    skipped_duplicate = "skipped_duplicate"
    stopped_budget = "stopped_budget"
    stopped_call_limit = "stopped_call_limit"
    stopped_phase_threshold = "stopped_phase_threshold"
    error_transient_models_list = "error_transient_models_list"
    error_transient_api = "error_transient_api"
    error_model_unavailable_all_fallback = "error_model_unavailable_all_fallback"
    error_permanent_api = "error_permanent_api"
    error_auth = "error_auth"
    error_bad_request = "error_bad_request"
    error_response_invalid = "error_response_invalid"
    error_missing_target_id = "error_missing_target_id"
    error_internal = "error_internal"
    db_error_blocked = "db_error_blocked"


# SPEC §9: error_kind → reason 対応表
_ERROR_KIND_TO_REASON: dict[str, str] = {
    "transient": Reasons.error_transient_api,
    "permanent_auth": Reasons.error_auth,
    "permanent_bad_request": Reasons.error_bad_request,
    "permanent_response_invalid": Reasons.error_response_invalid,
    "permanent_api": Reasons.error_permanent_api,
}

# フェーズ → クラス → 閾値
_PHASE_CLASS = {
    "research": "light",
    "requirements": "light",
    "test": "light",
    "design": "medium",
    "pre_impl": "medium",
    "implementation": "heavy",
}
_CLASS_THRESHOLD_KEY = {
    "light": "PHASE_THRESHOLD_LIGHT",
    "medium": "PHASE_THRESHOLD_MEDIUM",
    "heavy": "PHASE_THRESHOLD_HEAVY",
}
_CLASS_THRESHOLD_DEFAULT = {
    "light": 0.025,
    "medium": 0.10,
    "heavy": 0.15,
}


def _phase_threshold(model_class: str) -> float:
    key = _CLASS_THRESHOLD_KEY.get(model_class, "PHASE_THRESHOLD_LIGHT")
    return _cg_float(key, _CLASS_THRESHOLD_DEFAULT.get(model_class, 0.025))


class FinalizeStatus(str, Enum):
    """finalize() 完了状態（SPEC v2.10.1 §1.1）。"""

    OK_RECORDED = "ok_recorded"
    OK_RELEASED = "ok_released"
    IDEMPOTENT = "idempotent"
    STATE_MISMATCH = "state_mismatch"


@dataclass
class FinalizeResult:
    """finalize() の戻り値（SPEC v2.10.1 §1.2）。"""

    status: FinalizeStatus
    detail: str = ""


@dataclass
class Decision:
    """allowed() / finalize() で使用する判定結果（SPEC §7.1）。"""

    allowed: bool
    reason: str
    exit_code: int
    model: str
    model_class: str
    estimated_cost: float
    reservation_id: str | None
    dedup_key: str
    claim_id: str | None
    detail: str = ""
    script: str = ""
    phase: str = ""
    block_type: str = ""


def _fail_decision(
    reason: str,
    exit_code: int,
    script: str = "",
    phase: str = "",
    block_type: str = "",
    detail: str = "",
) -> Decision:
    return Decision(
        allowed=False,
        reason=reason,
        exit_code=exit_code,
        model="",
        model_class="",
        estimated_cost=0.0,
        reservation_id=None,
        dedup_key="",
        claim_id=None,
        detail=detail,
        script=script,
        phase=phase,
        block_type=block_type,
    )


def allowed(
    phase: str,
    block_type: str,
    target_id: str = "",
    est_in: int = 200,
    est_out: int = 300,
    model_hint: str | None = None,
    script: str = "",
) -> Decision:
    """SPEC §6 の実行順序 1〜7 を実行する（8 = 実LLM呼び出しは呼び出し側責務）。

    成功時(allowed=True)の Decision.reason は "ok" 固定。
    失敗時は SPEC §9 reason enum のいずれか。

    fail-close: ledger DB 読み取り失敗時は allowed=False（db_error_blocked）を返す。
    """
    import sqlite3 as _sqlite3

    from common.dedup import (
        claim_dedup as _claim_dedup,
    )
    from common.dedup import (
        compose_dedup_key,
        validate_target_id,
    )
    from common.dedup import (
        release_dedup as _release_dedup,
    )
    from common.ledger import _log_event_in_tx, _release_dedup_in_tx, _release_in_tx
    from common.ledger import can_spend as _can_spend
    from common.ledger import log_event as _log_event
    from common.ledger import reserve as _reserve
    from common.model_selector import ModelSelectionError, select_model
    from common.state_store import begin_immediate

    def _log(reason: str, detail: str = "") -> None:
        try:
            _log_event(reason, detail=detail, phase=phase, block_type=block_type, script=script)
        except Exception:
            pass

    def _notify(reason: str, detail: str = "") -> None:
        try:
            from common.notifier import notify

            notify(reason, detail=detail, phase=phase, block_type=block_type)
        except Exception:
            pass

    # ── Step 1: モデル選択 ──────────────────────────────────────
    try:
        sel = select_model(phase, model_hint=model_hint)
    except ModelSelectionError as e:
        _log(e.reason)
        _notify(e.reason)
        exit_code = 2
        return _fail_decision(e.reason, exit_code, script=script, phase=phase, block_type=block_type)
    except _sqlite3.OperationalError:
        _log(Reasons.error_internal, "lock_timeout")
        return _fail_decision(
            Reasons.error_internal, 2, script=script, phase=phase, block_type=block_type, detail="lock_timeout"
        )

    model = sel.model
    model_class = sel.model_class

    # ── Step 2: コスト推定 ──────────────────────────────────────
    try:
        estimated_cost = _estimate_cost(model, est_in, est_out)
    except Exception as e:
        _log(Reasons.error_internal, f"estimate_failed: {e}")
        return _fail_decision(
            Reasons.error_internal, 2, script=script, phase=phase, block_type=block_type, detail="estimate_failed"
        )

    # ── Step 3: 装置2 フェーズ別単発閾値 ─────────────────────────
    threshold = _phase_threshold(model_class)
    if estimated_cost > threshold:
        _log(Reasons.stopped_phase_threshold)
        _notify(Reasons.stopped_phase_threshold)
        d = _fail_decision(Reasons.stopped_phase_threshold, 1, script=script, phase=phase, block_type=block_type)
        d.model = model
        d.model_class = model_class
        d.estimated_cost = estimated_cost
        return d

    # ── Step 4: target_id 必須チェック ────────────────────────────
    try:
        validate_target_id(block_type, target_id)
    except ValueError as e:
        _log(Reasons.error_missing_target_id, str(block_type))
        _notify(Reasons.error_missing_target_id, str(block_type))
        return _fail_decision(
            Reasons.error_missing_target_id, 2, script=script, phase=phase, block_type=block_type, detail=str(e)
        )
    except _sqlite3.OperationalError:
        _log(Reasons.error_internal, "lock_timeout")
        return _fail_decision(
            Reasons.error_internal, 2, script=script, phase=phase, block_type=block_type, detail="lock_timeout"
        )

    # dedup_key 組み立て
    from common.ledger import _today_jst

    today = _today_jst()
    dedup_key = compose_dedup_key(today, block_type, phase, target_id)

    # ── Step 5: claim_dedup ────────────────────────────────────
    try:
        claim_id = _claim_dedup(dedup_key, ttl_sec=int(_cg_env("DEDUP_CLAIM_TTL_SEC", "3600")))
    except _sqlite3.OperationalError:
        _log(Reasons.error_internal, "lock_timeout")
        return _fail_decision(
            Reasons.error_internal, 2, script=script, phase=phase, block_type=block_type, detail="lock_timeout"
        )
    except Exception as e:
        _log(Reasons.error_internal, f"claim_dedup_error: {e}")
        return _fail_decision(
            Reasons.error_internal, 2, script=script, phase=phase, block_type=block_type, detail=str(e)
        )

    if claim_id is None:
        _log(Reasons.skipped_duplicate)
        return Decision(
            allowed=False,
            reason=Reasons.skipped_duplicate,
            exit_code=2,
            model="",
            model_class="",
            estimated_cost=0.0,
            reservation_id=None,
            dedup_key=dedup_key,
            claim_id=None,
            script=script,
            phase=phase,
            block_type=block_type,
        )

    # ── Step 6: reserve(DAILY_CALL_LIMIT) ─────────────────────
    try:
        reservation_id = _reserve(phase, block_type=block_type, target_id=target_id, script=script)
    except _sqlite3.OperationalError:
        _log(Reasons.error_internal, "lock_timeout")
        try:
            _release_dedup(claim_id)
        except Exception:
            pass
        return _fail_decision(
            Reasons.error_internal, 2, script=script, phase=phase, block_type=block_type, detail="lock_timeout"
        )
    except Exception as e:
        _log(Reasons.error_internal, str(e))
        try:
            _release_dedup(claim_id)
        except Exception:
            pass
        return _fail_decision(
            Reasons.error_internal, 2, script=script, phase=phase, block_type=block_type, detail=str(e)
        )

    if reservation_id is None:
        _log(Reasons.stopped_call_limit, phase)
        _notify(Reasons.stopped_call_limit, phase)
        try:
            _release_dedup(claim_id)
        except Exception:
            pass
        return Decision(
            allowed=False,
            reason=Reasons.stopped_call_limit,
            exit_code=1,
            model="",
            model_class="",
            estimated_cost=0.0,
            reservation_id=None,
            dedup_key=dedup_key,
            claim_id=None,
            script=script,
            phase=phase,
            block_type=block_type,
        )

    # ── Step 7: can_spend (グローバル予算) ──────────────────────
    db_read_error = False
    db_error_detail = ""
    try:
        budget_ok = _can_spend(est_in, est_out, model)
    except Exception as e:
        budget_ok = False
        db_read_error = True
        db_error_detail = str(e)

    if not budget_ok:
        detail_str = ""
        # 1) cleanup は単独で必達(失敗したら error_internal)
        try:
            with begin_immediate() as conn:
                _release_in_tx(conn, reservation_id)
                if claim_id is not None:
                    _release_dedup_in_tx(conn, claim_id)
        except Exception as e:
            msg = f"budget_cleanup_error:{e}"
            _log(Reasons.error_internal, msg)
            return _fail_decision(
                Reasons.error_internal,
                2,
                script=script,
                phase=phase,
                block_type=block_type,
                detail=msg,
            )

        if db_read_error:
            try:
                with begin_immediate() as conn:
                    _log_event_in_tx(
                        conn,
                        Reasons.db_error_blocked,
                        db_error_detail,
                        phase=phase,
                        block_type=block_type,
                        script=script,
                    )
            except Exception as e:
                db_error_detail = f"{db_error_detail}; log_error={e}"
            _notify(Reasons.db_error_blocked, db_error_detail)
            return Decision(
                allowed=False,
                reason=Reasons.db_error_blocked,
                exit_code=2,
                model="",
                model_class="",
                estimated_cost=0.0,
                reservation_id=reservation_id,
                dedup_key=dedup_key,
                claim_id=claim_id,
                detail=db_error_detail,
                script=script,
                phase=phase,
                block_type=block_type,
            )

        # 2) detail取得・stopped_budget記録はベストエフォート
        try:
            from common.ledger import _month_jst, _today_jst

            with begin_immediate() as conn:
                today = _today_jst()
                month = _month_jst()
                daily_row = conn.execute("SELECT daily_usd FROM daily_state WHERE date=?", (today,)).fetchone()
                monthly_row = conn.execute("SELECT monthly_usd FROM monthly_state WHERE month=?", (month,)).fetchone()
                daily = daily_row["daily_usd"] if daily_row else 0.0
                monthly = monthly_row["monthly_usd"] if monthly_row else 0.0
                detail_str = f"daily_usd={daily:.4f}, monthly_usd={monthly:.4f}"
                _log_event_in_tx(
                    conn,
                    Reasons.stopped_budget,
                    detail_str,
                    phase=phase,
                    block_type=block_type,
                    script=script,
                )
        except Exception as e:
            detail_str = f"budget_stop_with_partial_error:{e}"

        _notify(Reasons.stopped_budget, detail_str)
        return Decision(
            allowed=False,
            reason=Reasons.stopped_budget,
            exit_code=1,
            model="",
            model_class="",
            estimated_cost=0.0,
            reservation_id=reservation_id,
            dedup_key=dedup_key,
            claim_id=claim_id,
            detail=detail_str,
            script=script,
            phase=phase,
            block_type=block_type,
        )

    # ── 全チェック通過 ─────────────────────────────────────────
    return Decision(
        allowed=True,
        reason=Reasons.ok,
        exit_code=0,
        model=model,
        model_class=model_class,
        estimated_cost=estimated_cost,
        reservation_id=reservation_id,
        dedup_key=dedup_key,
        claim_id=claim_id,
        detail="",
        script=script,
        phase=phase,
        block_type=block_type,
    )


def finalize(
    decision: Decision,
    in_tokens: int = 0,
    out_tokens: int = 0,
    success: bool = True,
    error_kind: str = "",
) -> FinalizeResult:
    """実呼び出し結果に応じて record / release / confirm_dedup / release_dedup を実行する。

    全操作を単一 BEGIN IMMEDIATE トランザクションで原子的に実行（SPEC §3.2.2 / v2.10.1）。
    冪等/不整合は FinalizeResult で返す（SPEC v2.10.1 §6）。

    **呼び出し側 try/finally パターン（必須）**:

        decision = cost_guard.allowed(phase=..., block_type=..., target_id=...)
        if not decision.allowed:
            return  # or raise
        try:
            response = call_llm(...)
            cost_guard.finalize(decision, response.in_tokens, response.out_tokens, success=True)
        except TransientError as e:
            cost_guard.finalize(decision, 0, 0, success=False, error_kind="transient")
            raise
        except PermanentError as e:
            cost_guard.finalize(decision, 0, 0, success=False, error_kind="permanent_api")
            raise

    finalize() を呼ばずに return/raise すると reservation が解放されず DAILY_CALL_LIMIT を消費し続ける。
    必ず try/finally で保証すること（SPEC §5.6 / CLAUDE.md §2）。

    不正引数:
      - success=False かつ error_kind="" → raise ValueError
      - success=True  かつ error_kind!="" → raise ValueError
    """
    if not success and not error_kind:
        raise ValueError("error_kind required when success=False")
    if success and error_kind:
        raise ValueError("error_kind must be empty when success=True")

    if not decision.allowed:
        return FinalizeResult(status=FinalizeStatus.IDEMPOTENT)

    from common.ledger import (
        StateMismatchError,
        _confirm_dedup_in_tx,
        _load_finalize_state_in_tx,
        _record_in_tx,
        _release_dedup_in_tx,
        _release_in_tx,
    )
    from common.ledger import (
        log_event as _log_event,
    )
    from common.state_store import init_schema, open_conn

    init_schema()
    has_claim = decision.claim_id is not None
    is_mismatch = False
    mismatch_detail = ""

    conn = open_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            state = _load_finalize_state_in_tx(
                conn,
                decision.reservation_id,
                decision.claim_id,
            )

            if has_claim:
                if state.reservation_finalized and state.claim_confirmed:
                    conn.execute("COMMIT")
                    return FinalizeResult(status=FinalizeStatus.IDEMPOTENT)
            elif state.reservation_finalized:
                conn.execute("COMMIT")
                return FinalizeResult(status=FinalizeStatus.IDEMPOTENT)

            if not state.reservation_exists:
                is_mismatch = True
                mismatch_detail = "reservation_missing"
            elif has_claim and not state.claim_exists:
                is_mismatch = True
                mismatch_detail = "claim_missing"
            elif has_claim and state.reservation_finalized and not state.claim_confirmed:
                is_mismatch = True
                mismatch_detail = "partial_finalized_reservation_only"
            elif has_claim and not state.reservation_finalized and state.claim_confirmed:
                is_mismatch = True
                mismatch_detail = "partial_finalized_claim_only"

            if is_mismatch:
                conn.execute("ROLLBACK")
            elif success:
                if decision.reservation_id:
                    _record_in_tx(
                        conn,
                        in_tokens,
                        out_tokens,
                        decision.model,
                        decision.script,
                        phase=decision.phase,
                        reservation_id=decision.reservation_id,
                    )
                if has_claim:
                    _confirm_dedup_in_tx(conn, decision.claim_id, error=False)
                conn.execute("COMMIT")
            elif error_kind == "transient":
                if decision.reservation_id:
                    _release_in_tx(conn, decision.reservation_id)
                if has_claim:
                    _release_dedup_in_tx(conn, decision.claim_id)
                conn.execute("COMMIT")
            else:
                reason = _ERROR_KIND_TO_REASON.get(error_kind, Reasons.error_permanent_api)
                if decision.reservation_id:
                    _record_in_tx(
                        conn,
                        in_tokens,
                        out_tokens,
                        decision.model,
                        decision.script,
                        phase=decision.phase,
                        reservation_id=decision.reservation_id,
                        error=True,
                        reason=reason,
                    )
                if has_claim:
                    _confirm_dedup_in_tx(conn, decision.claim_id, error=True)
                conn.execute("COMMIT")
        except StateMismatchError as e:
            conn.execute("ROLLBACK")
            is_mismatch = True
            mismatch_detail = str(e)
    finally:
        conn.close()

    if is_mismatch:
        try:
            _log_event(
                reason=Reasons.error_internal,
                detail=f"finalize_state_mismatch:{mismatch_detail}",
                phase=decision.phase,
                block_type=decision.block_type,
                script=decision.script,
            )
        except Exception as log_exc:
            import logging

            logging.exception(
                "failed to persist finalize_state_mismatch log: %s",
                log_exc,
            )
        return FinalizeResult(
            status=FinalizeStatus.STATE_MISMATCH,
            detail=mismatch_detail,
        )

    if success:
        return FinalizeResult(status=FinalizeStatus.OK_RECORDED)
    if error_kind == "transient":
        return FinalizeResult(status=FinalizeStatus.OK_RELEASED)
    return FinalizeResult(status=FinalizeStatus.OK_RECORDED)
