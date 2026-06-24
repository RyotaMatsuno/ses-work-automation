# -*- coding: utf-8 -*-
"""
mail_pipeline 段階的復旧モード管理。

PROCESS_LIMIT / FETCH_LIMIT を段階的に引き上げる。
昇格は提案のみ（CEO確認後に適用）、縮退は即時実行。
RECOVERY_MODE=true の時のみ有効。
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = Path(__file__).resolve().parent
STATE_PATH = BASE / "recovery_state.json"

PHASE_SETTINGS = {
    "day0_emergency": {"process_limit": 10, "fetch_limit": 50},
    "day1_warmup": {"process_limit": 20, "fetch_limit": 100},
    "day2_warmup": {"process_limit": 30, "fetch_limit": 150},
    "day3_normal": {"process_limit": 50, "fetch_limit": 200},
}

NEXT_PHASE = {
    "day0_emergency": "day1_warmup",
    "day1_warmup": "day2_warmup",
    "day2_warmup": "day3_normal",
    "day3_normal": None,
}

PREV_PHASE = {
    "day3_normal": "day2_warmup",
    "day2_warmup": "day1_warmup",
    "day1_warmup": "day0_emergency",
    "day0_emergency": None,
}

PROMOTION_THRESHOLD = 4  # 連続成功回数で昇格提案
DEMOTION_THRESHOLD = 2  # 連続失敗回数で縮退

DEFAULT_STATE = {
    "current_phase": "day0_emergency",
    "phase_started_at": datetime.now().astimezone().isoformat(),
    "process_limit": 10,
    "fetch_limit": 50,
    "consecutive_success_count": 0,
    "consecutive_failure_count": 0,
    "last_metrics_ts": None,
    "promotion_proposal_pending": False,
    "promotion_proposal_to": None,
    "promotion_proposal_at": None,
    "promotion_decided_by": None,
    "promotion_decided_at": None,
}


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def get_limits(state: dict) -> tuple[int, int]:
    """(process_limit, fetch_limit) を返す。"""
    phase = state.get("current_phase", "day0_emergency")
    settings = PHASE_SETTINGS.get(phase, PHASE_SETTINGS["day0_emergency"])
    return settings["process_limit"], settings["fetch_limit"]


def _is_success(metrics: dict) -> bool:
    return (
        metrics.get("exit_code", 1) == 0 and metrics.get("notion_errors", 0) == 0 and metrics.get("imap_errors", 0) == 0
    )


def evaluate_promotion(state: dict, recent_metrics: dict) -> str:
    """
    state を更新し、提案アクションを返す。
    戻り値: "promote" | "demote" | "none"
    """
    state["last_metrics_ts"] = recent_metrics.get("ts_end") or datetime.now().isoformat()
    success = _is_success(recent_metrics)

    if success:
        state["consecutive_success_count"] += 1
        state["consecutive_failure_count"] = 0
    else:
        state["consecutive_failure_count"] += 1
        state["consecutive_success_count"] = 0

    current = state.get("current_phase", "day0_emergency")

    # 縮退判定（即時実行）
    if state["consecutive_failure_count"] >= DEMOTION_THRESHOLD:
        prev = PREV_PHASE.get(current)
        if prev and not state.get("promotion_proposal_pending"):
            _apply_phase(state, prev)
            return "demote"

    # 昇格提案（CEO確認待ち）
    if state["consecutive_success_count"] >= PROMOTION_THRESHOLD and not state.get("promotion_proposal_pending"):
        nxt = NEXT_PHASE.get(current)
        if nxt:
            state["promotion_proposal_pending"] = True
            state["promotion_proposal_to"] = nxt
            state["promotion_proposal_at"] = datetime.now().isoformat()
            save_state(state)
            return "promote"

    save_state(state)
    return "none"


def _apply_phase(state: dict, phase: str) -> None:
    settings = PHASE_SETTINGS.get(phase, PHASE_SETTINGS["day0_emergency"])
    state["current_phase"] = phase
    state["phase_started_at"] = datetime.now().astimezone().isoformat()
    state["process_limit"] = settings["process_limit"]
    state["fetch_limit"] = settings["fetch_limit"]
    state["consecutive_success_count"] = 0
    state["consecutive_failure_count"] = 0
    state["promotion_proposal_pending"] = False
    state["promotion_proposal_to"] = None
    save_state(state)


def confirm_promotion(state: dict, decision: str, decided_by: str = "CEO") -> bool:
    """
    昇格提案に対するCEO返答を処理する。
    decision: "OK" | "却下" | "明日まで"
    """
    if not state.get("promotion_proposal_pending"):
        return False

    if decision == "OK":
        target = state.get("promotion_proposal_to")
        if target:
            _apply_phase(state, target)
            state["promotion_decided_by"] = decided_by
            state["promotion_decided_at"] = datetime.now().isoformat()
            save_state(state)
        return True

    if decision == "却下":
        state["promotion_proposal_pending"] = False
        state["promotion_proposal_to"] = None
        save_state(state)
        return True

    if decision == "明日まで":
        state["promotion_proposal_at"] = (datetime.now() + timedelta(hours=24)).isoformat()
        state["promotion_proposal_pending"] = False
        save_state(state)
        return True

    return False


def manual_set_phase(phase: str) -> bool:
    """CEO LINE経由での手動フェーズ上書き。"""
    if phase not in PHASE_SETTINGS:
        return False
    state = load_state()
    _apply_phase(state, phase)
    return True


def build_promote_message(state: dict) -> str:
    current = state.get("current_phase", "day0_emergency")
    cur_set = PHASE_SETTINGS.get(current, {})
    nxt = state.get("promotion_proposal_to", "")
    nxt_set = PHASE_SETTINGS.get(nxt, {})
    count = state.get("consecutive_success_count", 0)
    return (
        f"[recovery_mode 昇格提案]\n"
        f"現状: {current} (process_limit={cur_set.get('process_limit')} / fetch_limit={cur_set.get('fetch_limit')})\n"
        f"提案: {nxt} (process_limit={nxt_set.get('process_limit')} / fetch_limit={nxt_set.get('fetch_limit')})\n"
        f"根拠: 直近{count}回連続成功(exit=0, notion_errors=0)\n"
        f"LINE返信:\n"
        f"  「昇格OK」→ 次回起動から新limit適用\n"
        f"  「却下」→ 提案保留、当面据え置き\n"
        f"  「明日まで」→ 24時間後に再提案"
    )


def build_demote_message(state: dict, prev_phase: str) -> str:
    current = state.get("current_phase", "day0_emergency")
    cur_set = PHASE_SETTINGS.get(current, {})
    count = state.get("consecutive_failure_count", 0)
    return (
        f"[recovery_mode 縮退実行]\n"
        f"前フェーズ: {prev_phase} → 現在: {current}\n"
        f"(process_limit={cur_set.get('process_limit')} / fetch_limit={cur_set.get('fetch_limit')})\n"
        f"根拠: {count}回連続失敗 → 自動縮退"
    )
