#!/usr/bin/env python3
"""Task AO: 新規案件のリアルタイムマッチングワーカー（5分ポーリング想定）。

matching_status=pending かつ案件タイマー以内の案件を取得し、
judge_with_meta() で MATCH/REVIEW/PARTIAL_MATCH 候補を通知する。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_MATCHING_V3 = Path(__file__).resolve().parent.parent
_SES_WORK = _MATCHING_V3.parent
for _p in (str(_MATCHING_V3), str(_SES_WORK)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import matcher  # noqa: E402
import structurer  # noqa: E402
from config import Config  # noqa: E402
from matching_cost_guard import CostGuard  # noqa: E402
from matcher import (  # noqa: E402
    SkillNormalizer,
    build_skill_index,
    exclude_unit_price_review_targets,
    filter_engineers_by_required_skills,
    partition_fresh_engineers,
)
from notifier import Notifier  # noqa: E402
from notion_client import NotionClient, realtime_match_window_hours  # noqa: E402
from processed_db import ProcessedDB  # noqa: E402

logger = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))
BASE_DIR = _MATCHING_V3
ALIASES_PATH = BASE_DIR / "skill_aliases.json"
LOG_DIR = BASE_DIR / "logs"
IDEMPOTENCY_PATH = LOG_DIR / "realtime_match_idempotency.jsonl"


def _today_key(case_id: str) -> str:
    today = datetime.now(JST).date().isoformat()
    return f"{case_id}:{today}"


def _already_processed(key: str) -> bool:
    if not IDEMPOTENCY_PATH.exists():
        return False
    for line in IDEMPOTENCY_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("key") == key:
            return True
    return False


def _mark_processed(key: str, case_id: str, match_count: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with IDEMPOTENCY_PATH.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "key": key,
                    "case_id": case_id,
                    "match_count": match_count,
                    "processed_at": datetime.now(JST).isoformat(),
                },
                ensure_ascii=False,
            )
            + "\n"
        )


def _case_within_window(case: dict[str, Any], now: datetime) -> bool:
    created_raw = case.get("created_time") or case.get("_created") or ""
    if not created_raw:
        return True
    try:
        created = datetime.fromisoformat(created_raw.replace("Z", "+00:00")).astimezone(JST)
    except ValueError:
        return True
    window = timedelta(hours=realtime_match_window_hours(case))
    return now - created <= window


def _notify_matsuno(config: Config, case_name: str, match_count: int) -> None:
    try:
        from line_webhook.line_bridge import push_or_log
    except ImportError:
        logger.warning("line_bridge unavailable; skip LINE notify")
        return
    uid = config.get("MATSUNO_LINE_USER_ID") or config.users.get("matsuno", {}).get("line_user_id")
    if not uid:
        logger.warning("MATSUNO_LINE_USER_ID not configured")
        return
    text = f"新規案件: {case_name} → MATCH {match_count}名"
    push_or_log(uid, text, task_id=f"realtime_match_{case_name[:20]}")


def run_once(*, dry_run: bool = False) -> dict[str, Any]:
    config = Config()
    db = ProcessedDB()
    cost_guard = CostGuard()
    normalizer = SkillNormalizer(ALIASES_PATH)
    notion = NotionClient(config)
    notifier = Notifier(config)

    try:
        active_engineers = notion.get_active_engineers()
    except RuntimeError as exc:
        logger.error("エンジニア取得失敗: %s", exc)
        return {"error": str(exc), "processed": 0}

    engineers = exclude_unit_price_review_targets(active_engineers, logger)
    engineers, staleness_excluded = partition_fresh_engineers(engineers, logger)
    if staleness_excluded:
        logger.info("鮮度フィルタ除外: %d名", staleness_excluded)
        if not dry_run:
            db.record_staleness_excluded(staleness_excluded)

    skill_index = build_skill_index(engineers, normalizer)
    now = datetime.now(JST)
    pending = notion.get_realtime_pending_cases(max_hours=6.0)
    processed = 0
    matched_total = 0

    for case in pending:
        case_id = case.get("id", "")
        if not case_id:
            continue
        if not _case_within_window(case, now):
            logger.info(
                "[タイムアウト] %s (window=%.1fh)",
                case.get("案件名", case_id),
                realtime_match_window_hours(case),
            )
            continue

        idem_key = _today_key(case_id)
        if _already_processed(idem_key):
            logger.info("skip idempotent: %s", idem_key)
            continue
        if db.is_processed(case_id):
            if not dry_run:
                notion.update_matching_status(case_id, "matched")
            continue

        case_name = case.get("案件名", case_id)
        body = case.get("案件詳細") or case.get("body") or ""
        if len(body) > 8000:
            if not dry_run:
                notion.update_matching_status(case_id, "skipped")
            _mark_processed(idem_key, case_id, 0)
            continue
        if not cost_guard.can_call(len(body) // 4 + 200, 300, target_id=case_id):
            logger.warning("コスト上限到達、リアルタイムワーカー停止")
            break

        if not dry_run:
            db.mark_api_called(case_id, case_name, case.get("_created", ""))

        try:
            case_json = structurer.structure_case(case, body, cost_guard, config)
        except Exception as exc:
            logger.error("structurer error %s: %s", case_id, exc)
            case_json = structurer.rule_based_fallback(case_name, body)
            if not structurer.is_recoverable(case_json):
                if not dry_run:
                    db.increment_retry(case_id)
                    db.update_status(case_id, "ERROR")
                    notion.update_matching_status(case_id, "error")
                continue

        candidates = filter_engineers_by_required_skills(
            engineers,
            normalizer,
            skill_index,
            case_json.get("required_skills") or [],
        )
        case_for_notify = {**case, **case_json, "case_json": case_json}
        results: list[dict[str, Any]] = []
        for engineer in candidates:
            judged = matcher.judge_with_meta(case_json, engineer, normalizer, case.get("担当者"))
            verdict = judged["verdict"]
            if verdict not in ("MATCH", "REVIEW", "PARTIAL_MATCH"):
                continue
            results.append(
                {
                    "engineer_id": engineer["id"],
                    "engineer_initial": (engineer.get("名前") or "")[:2],
                    "verdict": verdict,
                    "reasons": judged["reasons"],
                    "process_requirements": judged.get("process_requirements", []),
                    "engineer_price": engineer.get("単価（万円）"),
                    "score_components": judged.get("score_components", {}),
                }
            )
            if not dry_run:
                notifier.enqueue(case_for_notify, engineer, verdict, judged["reasons"])

        match_count = sum(1 for item in results if item["verdict"] == "MATCH")
        matched_total += match_count

        if dry_run:
            logger.info("[DRY] %s -> MATCH %d / candidates %d", case_name, match_count, len(results))
        else:
            db.update_status(case_id, "matched", results)
            notion.update_match_status(case_id, results)
            if match_count > 0:
                _notify_matsuno(config, case_name, match_count)

        _mark_processed(idem_key, case_id, match_count)
        processed += 1

    if not dry_run:
        notifier.flush()
        db.recompute_daily_stats()

    summary = {
        "pending_fetched": len(pending),
        "processed": processed,
        "match_count": matched_total,
    }
    logger.info("realtime worker done: %s", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Realtime match worker (Task AO)")
    parser.add_argument("--dry-run", action="store_true", help="Notion/LINE/DB更新なし")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "realtime_match_worker.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    result = run_once(dry_run=args.dry_run)
    logger.info("完了: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
