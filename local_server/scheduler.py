# -*- coding: utf-8 -*-
"""
jobz-command 内蔵の mail_pipeline 毎時スケジューラ。

【廃止】Windows Task Scheduler (SES_MailPipeline) に一本化済み。
command_server からの自動起動は行わない。直接実行も不可。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

DEPRECATED_MESSAGE = (
    "このスケジューラは廃止されました。Windows Task Scheduler (SES_MailPipeline) を使用してください。"
)

_DEPRECATED_RESPONSE: dict[str, Any] = {
    "ok": False,
    "reason": "deprecated_use_task_scheduler",
    "message": DEPRECATED_MESSAGE,
}

SES_WORK_DIR = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
JOB_STATE_DIR = SES_WORK_DIR / "job_state"
LOCK_PATH = JOB_STATE_DIR / "mail_pipeline_hourly.lock"
STATE_PATH = JOB_STATE_DIR / "mail_pipeline_hourly.json"
HOURLY_LOG_DIR = SES_WORK_DIR / "logs" / "mail_pipeline_hourly"
PIPELINE_BAT = SES_WORK_DIR / "wd_mail_pipeline.bat"

CATCH_UP_MAX_SLOTS = 3
HISTORY_MAX_ENTRIES = 100
POLL_INTERVAL_SEC = 30
HOUR_TOLERANCE_SEC = 60

_stop_event = threading.Event()
_scheduler_thread: threading.Thread | None = None
_run_lock = threading.Lock()
_current_run: dict[str, Any] | None = None

DEFAULT_STATE: dict[str, Any] = {
    "last_scheduled_slot": None,
    "last_started_at": None,
    "last_finished_at": None,
    "last_exit_code": None,
    "last_success_at": None,
    "last_skipped_slot": None,
    "history": [],
}


def _ensure_dirs() -> None:
    JOB_STATE_DIR.mkdir(parents=True, exist_ok=True)
    HOURLY_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _slot_iso(dt: datetime) -> str:
    return dt.replace(minute=0, second=0, microsecond=0).isoformat()


def _parse_slot(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def load_state() -> dict[str, Any]:
    _ensure_dirs()
    if not STATE_PATH.exists():
        state = dict(DEFAULT_STATE)
        save_state(state)
        return state
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("state読み込み失敗、初期化: %s", exc)
        data = dict(DEFAULT_STATE)
    for key, value in DEFAULT_STATE.items():
        data.setdefault(key, value if key != "history" else [])
    if not isinstance(data.get("history"), list):
        data["history"] = []
    return data


def save_state(state: dict[str, Any]) -> None:
    _ensure_dirs()
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(STATE_PATH)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_lock_pid() -> int | None:
    if not LOCK_PATH.exists():
        return None
    try:
        return int(LOCK_PATH.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def acquire_file_lock() -> bool:
    _ensure_dirs()
    pid = os.getpid()
    for _ in range(2):
        try:
            fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(pid).encode("utf-8"))
            os.close(fd)
            return True
        except FileExistsError:
            existing = _read_lock_pid()
            if existing is not None and _pid_alive(existing):
                return False
            try:
                LOCK_PATH.unlink(missing_ok=True)
            except OSError:
                return False
    return False


def release_file_lock() -> None:
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _hourly_log_path() -> Path:
    return HOURLY_LOG_DIR / f"{datetime.now():%Y-%m-%d}.log"


def _append_hourly_log(message: str) -> None:
    _ensure_dirs()
    line = f"{datetime.now().isoformat()} {message}\n"
    with open(_hourly_log_path(), "a", encoding="utf-8") as f:
        f.write(line)


def _append_history(state: dict[str, Any], entry: dict[str, Any]) -> None:
    history = state.setdefault("history", [])
    history.insert(0, entry)
    del history[HISTORY_MAX_ENTRIES:]


def _missed_slots(last_slot: datetime | None, now: datetime) -> list[datetime]:
    current = now.replace(minute=0, second=0, microsecond=0)
    if last_slot is None:
        return [current] if now.minute <= 1 or (now.minute == 0 and now.second <= HOUR_TOLERANCE_SEC) else []

    slots: list[datetime] = []
    cursor = last_slot + timedelta(hours=1)
    while cursor <= current:
        slots.append(cursor)
        cursor += timedelta(hours=1)
    return slots


def _next_due_at(now: datetime | None = None) -> str:
    now = now or datetime.now()
    base = now.replace(minute=0, second=0, microsecond=0)
    if now.minute == 0 and now.second <= HOUR_TOLERANCE_SEC:
        return base.isoformat()
    return (base + timedelta(hours=1)).isoformat()


def _pipeline_command() -> str:
    return f'cmd /c "{PIPELINE_BAT}"'


def _execute_pipeline(scheduled_slot: str, *, manual: bool = False) -> dict[str, Any]:
    global _current_run

    if not PIPELINE_BAT.exists():
        return {"ok": False, "reason": "pipeline_bat_missing", "scheduled_slot": scheduled_slot}

    if not acquire_file_lock():
        return {"ok": False, "reason": "already_running", "scheduled_slot": scheduled_slot}

    started_at = datetime.now().isoformat()
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_info = {
        "job_id": job_id,
        "scheduled_slot": scheduled_slot,
        "started_at": started_at,
        "manual": manual,
    }
    with _run_lock:
        _current_run = dict(run_info)

    _append_hourly_log(f"START job_id={job_id} slot={scheduled_slot} manual={manual}")
    logger.info("[scheduler] mail_pipeline START slot=%s manual=%s", scheduled_slot, manual)

    log_file = HOURLY_LOG_DIR / f"run_{job_id}.log"
    exit_code = 1
    try:
        with open(log_file, "w", encoding="utf-8") as log_f:
            log_f.write(f"[START] {started_at}\n")
            log_f.write(f"[SLOT] {scheduled_slot}\n")
            log_f.write(f"[CMD] {_pipeline_command()}\n")
            log_f.write("=" * 60 + "\n")
            log_f.flush()
            proc = subprocess.Popen(
                _pipeline_command(),
                shell=True,
                cwd=str(SES_WORK_DIR),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            exit_code = proc.wait()
            log_f.write("\n" + "=" * 60 + "\n")
            log_f.write(f"[END] exit_code={exit_code}\n")
    except Exception as exc:
        logger.exception("[scheduler] mail_pipeline 実行失敗: %s", exc)
        _append_hourly_log(f"ERROR job_id={job_id} error={exc}")
        exit_code = 1
    finally:
        release_file_lock()

    finished_at = datetime.now().isoformat()
    state = load_state()
    state["last_scheduled_slot"] = scheduled_slot
    state["last_started_at"] = started_at
    state["last_finished_at"] = finished_at
    state["last_exit_code"] = exit_code
    if exit_code == 0:
        state["last_success_at"] = finished_at

    history_entry = {
        "job_id": job_id,
        "scheduled_slot": scheduled_slot,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
        "manual": manual,
        "log_file": str(log_file),
    }
    _append_history(state, history_entry)
    save_state(state)

    with _run_lock:
        _current_run = None

    _append_hourly_log(f"DONE job_id={job_id} exit_code={exit_code} slot={scheduled_slot}")
    logger.info("[scheduler] mail_pipeline DONE exit_code=%s slot=%s", exit_code, scheduled_slot)
    return {"ok": exit_code == 0, "job_id": job_id, "exit_code": exit_code, "scheduled_slot": scheduled_slot}


def run_manual() -> dict[str, Any]:
    slot = _slot_iso(datetime.now())
    return _execute_pipeline(slot, manual=True)


def is_running() -> bool:
    with _run_lock:
        if _current_run is not None:
            return True
    pid = _read_lock_pid()
    return pid is not None and _pid_alive(pid)


def get_status() -> dict[str, Any]:
    state = load_state()
    return {
        "running": is_running(),
        "last_started_at": state.get("last_started_at"),
        "last_finished_at": state.get("last_finished_at"),
        "last_exit_code": state.get("last_exit_code"),
        "last_success_at": state.get("last_success_at"),
        "next_due_at": _next_due_at(),
        "last_scheduled_slot": state.get("last_scheduled_slot"),
        "last_skipped_slot": state.get("last_skipped_slot"),
    }


def get_history(limit: int = 20) -> list[dict[str, Any]]:
    limit = max(1, min(limit, HISTORY_MAX_ENTRIES))
    state = load_state()
    return list(state.get("history", [])[:limit])


def _process_due_slots(now: datetime, *, catch_up: bool) -> None:
    if is_running():
        return

    state = load_state()
    last_slot = _parse_slot(state.get("last_scheduled_slot"))
    missed = _missed_slots(last_slot, now)

    if not missed:
        return

    if catch_up:
        to_run = missed[:CATCH_UP_MAX_SLOTS]
        if len(missed) > CATCH_UP_MAX_SLOTS:
            skipped = _slot_iso(missed[CATCH_UP_MAX_SLOTS])
            state["last_skipped_slot"] = skipped
            save_state(state)
            _append_hourly_log(f"SKIP catch-up overflow skipped_from={skipped}")
            logger.warning("[scheduler] catch-up上限超過 skipped_from=%s", skipped)
    else:
        if now.minute > 1 and not (now.minute == 0 and now.second <= HOUR_TOLERANCE_SEC):
            return
        to_run = [missed[-1]]

    for slot_dt in to_run:
        if is_running():
            break
        result = _execute_pipeline(_slot_iso(slot_dt))
        if result.get("reason") == "already_running":
            break


def _scheduler_loop() -> None:
    logger.info("[scheduler] mail_pipeline hourly scheduler 開始")
    _process_due_slots(datetime.now(), catch_up=True)

    while not _stop_event.is_set():
        now = datetime.now()
        at_hour_boundary = now.minute == 0 and now.second <= HOUR_TOLERANCE_SEC
        if at_hour_boundary:
            _process_due_slots(now, catch_up=False)
        _stop_event.wait(POLL_INTERVAL_SEC)

    logger.info("[scheduler] mail_pipeline hourly scheduler 停止")


def start_scheduler() -> None:
    """廃止: Task Scheduler に一本化。何もしない。"""
    logger.warning("[scheduler] %s", DEPRECATED_MESSAGE)


def stop_scheduler() -> None:
    _stop_event.set()
    if _scheduler_thread is not None:
        _scheduler_thread.join(timeout=5)


def handle_get(path: str) -> tuple[int, dict[str, Any]]:
    parsed = urlparse(path)
    if parsed.path == "/jobs/mail_pipeline/status":
        status = get_status()
        status["deprecated"] = True
        status["message"] = DEPRECATED_MESSAGE
        return 200, status
    if parsed.path == "/jobs/mail_pipeline/history":
        qs = parse_qs(parsed.query)
        limit = int(qs.get("limit", ["20"])[0])
        return 200, {"history": get_history(limit), "deprecated": True, "message": DEPRECATED_MESSAGE}
    return 404, {"error": "not found"}


def handle_post(path: str) -> tuple[int, dict[str, Any]]:
    if path == "/jobs/mail_pipeline/run":
        logger.warning("[scheduler] manual run rejected: %s", DEPRECATED_MESSAGE)
        return 410, dict(_DEPRECATED_RESPONSE)
    return 404, {"error": "not found"}


if __name__ == "__main__":
    print(DEPRECATED_MESSAGE)
    sys.exit(0)
