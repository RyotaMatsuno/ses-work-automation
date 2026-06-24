#!/usr/bin/env python3
"""nightly_jobz メインオーケストレーター (Phase 1)."""

from __future__ import annotations

import atexit
import json
import logging
import msvcrt
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import IO, Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nightly_jobz import config
from nightly_jobz.notion_queue import fetch_queued_tasks
from nightly_jobz.task_processor import ProcessResult, dispatch_task

JST = timezone(timedelta(hours=9))
_lock_fh: IO[str] | None = None


def _setup_logging() -> Path:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = config.LOG_DIR / f"nightly_{datetime.now(JST).strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    return log_path


def _rotate_logs() -> None:
    if not config.LOG_DIR.exists():
        return
    cutoff = datetime.now(JST) - timedelta(days=config.LOG_RETENTION_DAYS)
    for path in config.LOG_DIR.glob("nightly_*.log"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=JST)
            if mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def acquire_lock() -> IO[str]:
    global _lock_fh
    os.makedirs(os.path.dirname(config.NIGHTLY_LOCK_PATH), exist_ok=True)
    fh = open(config.NIGHTLY_LOCK_PATH, "w", encoding="utf-8")
    try:
        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        _lock_fh = fh
        return fh
    except OSError:
        fh.close()
        raise RuntimeError("lock_exists")


def release_lock() -> None:
    global _lock_fh
    if _lock_fh is None:
        return
    try:
        msvcrt.locking(_lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    try:
        _lock_fh.close()
    except OSError:
        pass
    _lock_fh = None
    try:
        if os.path.exists(config.NIGHTLY_LOCK_PATH):
            os.remove(config.NIGHTLY_LOCK_PATH)
    except OSError:
        pass


def _build_briefing(
    results: list[ProcessResult],
    *,
    dry_run: bool,
    run_cost: config.RunCostTracker,
) -> dict[str, Any]:
    counts = {"done": 0, "review": 0, "blocked": 0, "queued": 0}
    items: list[dict[str, Any]] = []
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
        item: dict[str, Any] = {
            "task_id": result.task_id,
            "type": result.task_type,
            "title": result.title,
            "status": result.status,
        }
        if result.result_path:
            item["result_path"] = result.result_path
        if result.note:
            item["note"] = result.note
        items.append(item)

    return {
        "date": datetime.now(JST).date().isoformat(),
        "dry_run": dry_run,
        "tasks_processed": len(results),
        "tasks_done": counts.get("done", 0),
        "tasks_review": counts.get("review", 0),
        "tasks_blocked": counts.get("blocked", 0),
        "tasks_queued": counts.get("queued", 0),
        "cost_usd": round(run_cost.total_usd, 4),
        "items": items,
    }


def _save_briefing(payload: dict[str, Any]) -> Path:
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.LOG_DIR / f"briefing_{datetime.now(JST).strftime('%Y%m%d')}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def run_nightly(*, dry_run: bool | None = None) -> dict[str, Any]:
    dry = config.get_dry_run() if dry_run is None else dry_run
    logger = logging.getLogger("nightly_jobz")
    run_cost = config.RunCostTracker()
    started = time.time()
    results: list[ProcessResult] = []

    logger.info(
        "nightly_jobz start dry_run=%s budget=$%.2f",
        dry,
        run_cost.limit_usd,
    )

    tasks = fetch_queued_tasks(limit=20)
    logger.info("queued tasks: %d", len(tasks))

    for task in tasks:
        if time.time() - started > config.MAX_RUNTIME_SECONDS:
            logger.warning("max runtime reached, stopping")
            break
        if not run_cost.can_spend(0.05):
            logger.warning("nightly budget exhausted at $%.4f", run_cost.total_usd)
            break
        try:
            result = dispatch_task(task, dry_run=dry, run_cost=run_cost)
            results.append(result)
            logger.info("processed %s type=%s status=%s", task.task_id, task.task_type, result.status)
        except Exception as exc:
            logger.error("task failed %s: %s", task.task_id, exc)
            results.append(
                ProcessResult(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    title=task.task_id,
                    status="blocked",
                    note=str(exc)[:200],
                )
            )

    briefing = _build_briefing(results, dry_run=dry, run_cost=run_cost)
    briefing_path = _save_briefing(briefing)
    logger.info("briefing saved: %s", briefing_path)
    return briefing


def main() -> int:
    config.load_env()
    _rotate_logs()
    _setup_logging()
    logger = logging.getLogger("nightly_jobz")
    # Fail-safe: 本番モード（DRY_RUN=False）は明示的なALLOW_PROD_WRITESが必要
    if not config.get_dry_run():
        if os.environ.get("ALLOW_PROD_WRITES") != "YES":
            logger.error(
                "REFUSED: dry_run=False but ALLOW_PROD_WRITES!=YES. "
                "Set ALLOW_PROD_WRITES=YES to permit production writes."
            )
            return 1

    atexit.register(release_lock)
    try:
        acquire_lock()
    except RuntimeError:
        logger.info("別プロセスが実行中 - スキップ")
        return 0

    try:
        run_nightly()
        return 0
    except Exception as exc:
        logger.exception("nightly_jobz failed: %s", exc)
        return 1
    finally:
        release_lock()


if __name__ == "__main__":
    raise SystemExit(main())
