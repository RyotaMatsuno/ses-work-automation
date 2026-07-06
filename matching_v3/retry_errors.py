"""ERRORステータス案件を再マッチングするバッチスクリプト。

AB Phase 3: matching_v3.pyのマッチ品質修正がデプロイされた後に実行すること。

Usage:
    python retry_errors.py                    # dry-run, batch-size=50
    python retry_errors.py --execute          # 本番実行
    python retry_errors.py --batch-size 20   # バッチサイズ変更
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from script_bootstrap import bootstrap

BASE_DIR, SES_WORK = bootstrap()
RESULTS_DIR = SES_WORK / "research_results"
JST = timezone(timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

COSTGUARD_BATCH_LIMIT_USD = 2.0


def _fetch_error_cases(db_path: Path, batch_size: int) -> list[dict[str, Any]]:
    """processed_casesからbusiness_status=ERROR かつ retry_count<3 を取得。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT case_id, email_subject, retry_count
            FROM processed_cases
            WHERE business_status = 'ERROR'
              AND COALESCE(retry_count, 0) < 3
            ORDER BY updated_at ASC
            LIMIT ?
            """,
            (batch_size,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _fetch_error_date_distribution(db_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT date(updated_at) AS stat_date, COUNT(*) AS cnt
            FROM processed_cases
            WHERE business_status = 'ERROR'
              AND COALESCE(retry_count, 0) < 3
            GROUP BY date(updated_at)
            ORDER BY stat_date
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _check_costguard(cost_guard) -> bool:
    """日次残予算が COSTGUARD_BATCH_LIMIT_USD を超えたら中断。"""
    daily = cost_guard._get_daily_stats()
    spent = float(daily.get("total_cost_usd", 0.0))
    remaining = cost_guard.DAILY_COST_LIMIT_USD - spent
    if remaining < COSTGUARD_BATCH_LIMIT_USD:
        logger.warning(
            "CostGuard: 残予算 $%.4f < 閾値 $%.2f → 中断", remaining, COSTGUARD_BATCH_LIMIT_USD
        )
        return False
    return True


def run_retry(batch_size: int = 50, execute: bool = False) -> dict[str, Any]:
    from config import Config
    from matching_cost_guard import CostGuard
    from notion_client import NotionClient
    from processed_db import ProcessedDB
    import structurer
    import matcher
    from matcher import (
        SkillNormalizer,
        build_skill_index,
        exclude_unit_price_review_targets,
        filter_engineers_by_required_skills,
        partition_fresh_engineers,
        prepare_engineer_skills,
        resolve_case_required_skills,
    )
    from notifier import Notifier

    config = Config()
    db = ProcessedDB()

    error_cases = _fetch_error_cases(db.db_path, batch_size)
    date_distribution = _fetch_error_date_distribution(db.db_path)
    logger.info("ERROR件数: %d (batch_size=%d)", len(error_cases), batch_size)

    if not execute:
        stats: dict[str, Any] = {
            "batch_size": batch_size,
            "error_cases_found": len(error_cases),
            "processed": 0,
            "matched": 0,
            "ng": 0,
            "re_errored": 0,
            "skipped_costguard": 0,
            "execute": False,
            "date_distribution": date_distribution,
        }
        _write_report(stats)
        return stats

    cost_guard = CostGuard()
    notion = NotionClient(config)
    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")
    notifier = Notifier(config)

    if not _check_costguard(cost_guard):
        stats = {
            "batch_size": batch_size,
            "error_cases_found": len(error_cases),
            "processed": 0,
            "matched": 0,
            "ng": 0,
            "re_errored": 0,
            "skipped_costguard": 1,
            "execute": True,
            "date_distribution": date_distribution,
            "status": "aborted_costguard",
        }
        _write_report(stats)
        return stats

    if not error_cases:
        logger.info("リトライ対象なし")
        stats = {
            "batch_size": batch_size,
            "error_cases_found": 0,
            "processed": 0,
            "matched": 0,
            "ng": 0,
            "re_errored": 0,
            "skipped_costguard": 0,
            "execute": True,
            "date_distribution": date_distribution,
            "status": "no_targets",
        }
        _write_report(stats)
        return stats

    try:
        active_engineers = notion.get_active_engineers()
    except RuntimeError as exc:
        logger.error("エンジニア取得失敗: %s", exc)
        return {"status": "engineer_fetch_failed", "processed": 0}

    engineers = exclude_unit_price_review_targets(active_engineers, logger)
    engineers, _ = partition_fresh_engineers(engineers, logger)
    engineers = [prepare_engineer_skills(eng, normalizer) for eng in engineers]
    skill_index = build_skill_index(engineers, normalizer)

    stats: dict[str, Any] = {
        "batch_size": batch_size,
        "error_cases_found": len(error_cases),
        "processed": 0,
        "matched": 0,
        "ng": 0,
        "re_errored": 0,
        "skipped_costguard": 0,
        "execute": True,
        "date_distribution": date_distribution,
    }

    case_ids = [row["case_id"] for row in error_cases]
    notion_cases = _fetch_notion_cases(notion, case_ids)

    for row in error_cases:
        case_id = row["case_id"]
        case = notion_cases.get(case_id)
        if not case:
            logger.warning("Notion案件取得不可: %s", case_id)
            db.increment_retry(case_id)
            stats["re_errored"] += 1
            continue

        body = case.get("案件詳細") or case.get("body") or ""
        if not cost_guard.can_call(len(body) // 4 + 200, 300, target_id=case_id):
            logger.warning("CostGuard: case_id=%s をスキップ", case_id)
            stats["skipped_costguard"] += 1
            break

        try:
            case_json = structurer.structure_case(case, body, cost_guard)
        except Exception as exc:
            logger.error("Structurer error case=%s: %s", case_id, exc)
            db.increment_retry(case_id)
            stats["re_errored"] += 1
            continue

        required_skills, skills_source = resolve_case_required_skills(case, case_json, normalizer)
        case_json["required_skills"] = required_skills
        if not required_skills:
            db.update_status(case_id, "SKIPPED")
            logger.info("SKIPPED (no_skills): case=%s", case_id)
            stats["processed"] += 1
            continue

        candidates = filter_engineers_by_required_skills(engineers, normalizer, skill_index, required_skills)
        results: list[dict[str, Any]] = []
        for engineer in candidates:
            from staleness_checker import check as staleness_check
            judged = matcher.judge_with_meta(case_json, engineer, normalizer, case.get("担当者"))
            if judged["verdict"] in ("MATCH", "REVIEW", "PARTIAL_MATCH"):
                results.append({
                    "engineer_id": engineer["id"],
                    "verdict": judged["verdict"],
                    "score": float(judged.get("score", 0.0)),
                })

        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        if len(results) > 20:
            results = results[:20]

        final_status = "matched" if results else "ng"
        if execute:
            db.update_status(case_id, final_status, results)
            notion.update_match_status(case_id, results)
        stats["processed"] += 1
        stats[final_status if final_status in ("matched", "ng") else "ng"] += 1
        logger.info("retry done: case=%s status=%s matches=%d", case_id, final_status, len(results))

    _write_report(stats)
    return stats


def _fetch_notion_cases(notion, case_ids: list[str]) -> dict[str, Any]:
    """case_idリストからNotionで案件を取得してdict化。"""
    result: dict[str, Any] = {}
    for case_id in case_ids:
        try:
            page = notion._request("GET", f"pages/{case_id}")
            parsed = notion._parse_case_page(page)
            result[case_id] = parsed
        except Exception as exc:
            logger.warning("案件取得失敗 case_id=%s: %s", case_id, exc)
        time.sleep(0.3)
    return result


def _write_report(stats: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"retry_errors_report_{ts}.md"
    mode = "本番実行" if stats.get("execute") else "dry-run"
    lines = [
        f"# ERRORリトライレポート ({mode})",
        f"",
        f"- ERROR件数: {stats.get('error_cases_found', 0)}",
        f"- 処理件数: {stats.get('processed', 0)}",
        f"- マッチ成功: {stats.get('matched', 0)}",
        f"- NG: {stats.get('ng', 0)}",
        f"- 再エラー: {stats.get('re_errored', 0)}",
        f"- コスト中断: {stats.get('skipped_costguard', 0)}",
        "",
        "## 日付分布",
    ]
    for row in stats.get("date_distribution") or []:
        lines.append(f"- {row.get('stat_date', '?')}: {row.get('cnt', 0)}件")
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("レポート: %s", path)


def main() -> int:
    parser = argparse.ArgumentParser(description="ERRORリトライバッチ")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()
    result = run_retry(batch_size=args.batch_size, execute=args.execute)
    logger.info("完了: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
