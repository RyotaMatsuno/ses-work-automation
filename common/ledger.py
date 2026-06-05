from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent  # ses_work/
STATE_FILE = Path(__file__).resolve().parent / "cost_state.json"
COST_LOG = BASE_DIR / "usage_tracker" / "cost_log.jsonl"
ENV_PATH = BASE_DIR / "config" / ".env"
_ENV = dotenv_values(ENV_PATH, encoding="utf-8") if ENV_PATH.exists() else {}

def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name) or _ENV.get(name) or default)
    except (TypeError, ValueError):
        return default


# グローバル上限
DAILY_HARD_USD = _float_env("COST_GUARD_DAILY_USD", 1.0)
MONTHLY_USD = _float_env("COST_GUARD_MONTHLY_USD", 6.0)

_DEFAULT_RATE = (1.0, 5.0)


def _estimate(in_tokens: int, out_tokens: int, model: str) -> float:
    model_lower = (model or "").lower()
    if "haiku" in model_lower:
        r = (1.0, 5.0)
    elif "sonnet" in model_lower:
        r = (3.0, 15.0)
    elif model_lower.startswith("gpt"):
        r = (0.10, 0.40)
    else:
        r = _DEFAULT_RATE
    return in_tokens * r[0] / 1_000_000 + out_tokens * r[1] / 1_000_000


def _now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_state() -> dict:
    today = _now_date()
    month = _now_month()
    s: dict = {}
    if STATE_FILE.exists():
        try:
            s = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            s = {}
    # 月またぎリセット
    if s.get("month") != month:
        s = {"date": today, "month": month, "daily_usd": 0.0, "monthly_usd": 0.0, "daily_calls": 0}
    # 日またぎリセット
    elif s.get("date") != today:
        s = {"date": today, "month": month, "daily_usd": 0.0, "monthly_usd": s.get("monthly_usd", 0.0), "daily_calls": 0}
    return s


def _save_state(s: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)


def _append_log(entry: dict) -> None:
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def can_spend(est_in: int = 200, est_out: int = 300,
              model: str = "") -> bool:
    """API呼び出し前に確認。Falseならスキップすること。"""
    s = _load_state()
    est = _estimate(est_in, est_out, model)
    if s["daily_usd"] + est > DAILY_HARD_USD:
        _append_log({
            "ts": datetime.now(timezone.utc).isoformat(),
            "script": "cost_guard",
            "model": model,
            "input_tokens": est_in,
            "output_tokens": est_out,
            "cost_usd": est,
            "blocked": True,
            "reason": "daily_limit",
        })
        return False
    if s["monthly_usd"] + est > MONTHLY_USD:
        _append_log({
            "ts": datetime.now(timezone.utc).isoformat(),
            "script": "cost_guard",
            "model": model,
            "input_tokens": est_in,
            "output_tokens": est_out,
            "cost_usd": est,
            "blocked": True,
            "reason": "monthly_limit",
        })
        return False
    return True


def record(in_tokens: int, out_tokens: int, model: str, script: str) -> None:
    """API呼び出し成功後に必ず呼ぶ。コストを記録する。"""
    cost = _estimate(in_tokens, out_tokens, model)
    s = _load_state()
    s["daily_usd"] = round(s["daily_usd"] + cost, 8)
    s["monthly_usd"] = round(s["monthly_usd"] + cost, 8)
    s["daily_calls"] = s.get("daily_calls", 0) + 1
    _save_state(s)
    _append_log({
        "ts":            datetime.now(timezone.utc).isoformat(),
        "script":        script,
        "model":         model,
        "input_tokens":  in_tokens,
        "output_tokens": out_tokens,
        "cost_usd":      cost,
    })


def daily_total() -> float:
    return _load_state()["daily_usd"]


def monthly_total() -> float:
    return _load_state()["monthly_usd"]
