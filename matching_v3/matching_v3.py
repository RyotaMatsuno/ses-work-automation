from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_MATCHING_V3_DIR = str(_Path(__file__).resolve().parent)
_SES_WORK = str(_Path(__file__).resolve().parent.parent)
if _MATCHING_V3_DIR not in _sys.path:
    _sys.path.insert(0, _MATCHING_V3_DIR)
if _SES_WORK not in _sys.path:
    _sys.path.insert(1, _SES_WORK)

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jpholiday
import matcher
import structurer
from skill_gate import (
    evaluate_matchability,
    extract_raw_required_skills,
    normalize_technical_skills,
)
from matcher import (
    SkillNormalizer,
    build_skill_index,
    canonicalize_skill_list,
    exclude_unit_price_review_targets,
    filter_candidates_3layer,
    filter_engineers_by_required_skills,
    filter_fresh_engineers,
    log_case_skills_debug,
    log_engineer_match_debug,
    partition_fresh_engineers,
    prepare_engineer_skills,
    resolve_case_required_skills,
)
from staleness_checker import check as staleness_check
from notifier import Notifier
from notion_client import NotionClient
from processed_db import ProcessedDB

from config import Config
from matching_cost_guard import MATCHING_BATCH_PHASE, CostGuard

BASE_DIR = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)
LEGACY_MATCHING_PHASE = "matching"


def _fetch_matching_pending_entries(limit: int = 200) -> list[dict[str, Any]]:
    """matching_batch と旧 matching の保留エントリを FIFO で返す。"""
    from common.ledger import fetch_pending_queue

    batch_entries = fetch_pending_queue(phase=MATCHING_BATCH_PHASE, limit=limit)
    legacy_entries = fetch_pending_queue(phase=LEGACY_MATCHING_PHASE, limit=limit)
    return sorted(legacy_entries + batch_entries, key=lambda item: item["id"])


def _count_matching_pending() -> int:
    from common.ledger import count_pending_queue

    return count_pending_queue(phase=MATCHING_BATCH_PHASE) + count_pending_queue(
        phase=LEGACY_MATCHING_PHASE
    )


class LockFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    STALE_MINUTES = 30

    def acquire(self) -> bool:
        # 古いロック（STALE_MINUTES超）は異常終了の残骸とみなし奪取する
        if self.path.exists():
            try:
                import time as _t

                age_min = (_t.time() - self.path.stat().st_mtime) / 60
                if age_min > self.STALE_MINUTES:
                    self.path.unlink()
            except OSError:
                pass
        try:
            fd = self.path.open("x", encoding="utf-8")
            fd.write(str(datetime.now(JST).isoformat()))
            fd.close()
            self.acquired = True
            return True
        except FileExistsError:
            return False

    def release(self) -> None:
        if self.acquired and self.path.exists():
            self.path.unlink()
            self.acquired = False


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _setup_logging()
    if args.recompute_stats:
        db = ProcessedDB()
        if args.stat_date:
            stats = db.recompute_daily_stats(args.stat_date)
            logger.info("daily_stats recomputed: %s", stats)
        else:
            stats_list = db.backfill_daily_stats()
            logger.info("daily_stats backfilled for %d dates", len(stats_list))
        return 0

    if not _is_business_day():
        logger.info("非稼働日のためスキップ")
        return 0

    if args.reprocess_today and not args.dry_run:
        logger.error("--reprocess-today は --dry-run と併用してください")
        return 1

    lock = LockFile(BASE_DIR / "matching_v3.lock")
    if not lock.acquire():
        logger.warning("別プロセスが実行中")
        return 0

    try:
        if args.dry_run and args.reprocess_today:
            _run_reprocess_today_dry()
        elif args.dry_run:
            _run_dry(args.input)
        else:
            _run_live()
    finally:
        lock.release()
    return 0


def _notify_matching_abort(message: str) -> None:
    """提案対象フラグ取得失敗などでマッチング中断時に松野へ通知する。"""
    try:
        from line_webhook.line_bridge import push_or_log

        config = Config()
        matsuno_uid = config.get("MATSUNO_LINE_USER_ID") or config.users.get("matsuno", {}).get("line_user_id")
        if matsuno_uid:
            push_or_log(matsuno_uid, message, task_id="matching_v3_abort")
    except Exception as exc:
        logger.error("マッチング中断通知の送信に失敗: %s", exc)


def _run_live() -> None:
    from flag_auto_updater.run_flag_updater import run_flag_updater

    flag_exit = run_flag_updater()
    if flag_exit != 0:
        logger.error("提案対象フラグ更新が失敗したため matching_v3 を中断 (exit=%s)", flag_exit)
        return

    db = ProcessedDB()
    cost_guard = CostGuard()
    notifier = Notifier()
    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")
    notion = NotionClient()

    cases = notion.get_new_cases(days=4)

    # pending_queue: 失効処理 + 優先ソート
    pending_by_target: dict[str, int] = {}
    try:
        from common.ledger import expire_old_pending

        expire_old_pending(7)
        pq_count = _count_matching_pending()
        logger.info("pending_queue (matching_batch): %d件", pq_count)
        if pq_count > 0:
            pending_entries = _fetch_matching_pending_entries(limit=200)
            pending_by_target = {
                e["target_id"]: e["id"] for e in pending_entries if e.get("target_id")
            }
            pending_ids = set(pending_by_target)
            if pending_ids:
                priority_cases = [c for c in cases if c.get("id") in pending_ids]
                rest_cases = [c for c in cases if c.get("id") not in pending_ids]
                cases = priority_cases + rest_cases
                logger.info("pending_queue: %d件を先頭に移動", len(priority_cases))
    except Exception as pq_err:
        logger.error("pending_queue 確認エラー: %s", pq_err)

    try:
        active_engineers = notion.get_active_engineers()
    except RuntimeError as exc:
        logger.error("マッチング中断: %s", exc)
        _notify_matching_abort(f"[matching_v3 中断]\n{exc}")
        return
    before_count = len(active_engineers)
    engineers = exclude_unit_price_review_targets(active_engineers, logger)
    excluded_count = before_count - len(engineers)
    if excluded_count:
        logger.info("単価REVIEW除外 %d件", excluded_count)
    _process_cases(
        cases,
        engineers,
        db,
        cost_guard,
        normalizer,
        notifier,
        notion=notion,
        dry_run=False,
        pending_by_target=pending_by_target,
    )
    db.recompute_daily_stats()
    notifier.flush()
    _run_unknown_skill_discovery()


def _run_reprocess_today_dry() -> None:
    source_db = ProcessedDB()
    case_ids = _load_reprocess_today_case_ids(source_db)
    if not case_ids:
        logger.warning("reprocess-today: 対象案件なし")
        return

    structured_cache = _load_structured_cache()
    notion = NotionClient()
    notion_cases = _fetch_notion_cases_for_reprocess(notion, case_ids)
    cases: list[dict[str, Any]] = []
    for case_id in case_ids:
        case = notion_cases.get(case_id)
        if not case:
            continue
        cached = structured_cache.get(case_id)
        if cached:
            case["_cached_case_json"] = cached
        cases.append(case)

    logger.info("reprocess-today: %d件を再マッチング", len(cases))
    db = ProcessedDB(BASE_DIR / "logs" / "reprocess_today.db")
    cost_guard = CostGuard(BASE_DIR / "logs" / "phase0_cost_log.jsonl")
    notifier = Notifier(Config())
    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")

    try:
        active_engineers = notion.get_active_engineers()
    except RuntimeError as exc:
        logger.error("マッチング中断: %s", exc)
        _notify_matching_abort(f"[matching_v3 中断]\n{exc}")
        return
    before_count = len(active_engineers)
    engineers = exclude_unit_price_review_targets(active_engineers, logger)
    excluded_count = before_count - len(engineers)
    if excluded_count:
        logger.info("単価REVIEW除外 %d件", excluded_count)

    mass_stats = _process_cases(
        cases,
        engineers,
        db,
        cost_guard,
        normalizer,
        notifier,
        notion=None,
        dry_run=True,
        reprocess_today=True,
    )
    logger.info(
        "reprocess-today完了: mass_match_30plus=%d avg_matches=%.1f",
        mass_stats.get("mass_match_30plus", 0),
        mass_stats.get("avg_matches", 0.0),
    )


def _run_dry(input_path: str | None) -> None:
    db = ProcessedDB(BASE_DIR / "logs" / "phase0_processed.db")
    cost_guard = CostGuard(BASE_DIR / "logs" / "phase0_cost_log.jsonl")
    notifier = Notifier(Config())
    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")
    cases, engineers = _load_dry_input(input_path)
    if not engineers:
        # JSONL入力の場合はNotionから実エンジニアを取得（Phase0精度評価に必要）
        notion_client = NotionClient(Config())
        try:
            active_engineers = notion_client.get_active_engineers()
        except RuntimeError as exc:
            logger.error("マッチング中断: %s", exc)
            _notify_matching_abort(f"[matching_v3 中断]\n{exc}")
            return
        before_count = len(active_engineers)
        engineers = exclude_unit_price_review_targets(active_engineers, logger)
        excluded_count = before_count - len(engineers)
        if excluded_count:
            logger.info("単価REVIEW除外 %d件", excluded_count)
        logger.info("dry-run: fetched %d engineers from Notion", len(engineers))
    else:
        fresh_engineers = filter_fresh_engineers(engineers, logger)
        before_count = len(fresh_engineers)
        engineers = exclude_unit_price_review_targets(fresh_engineers, logger)
        excluded_count = before_count - len(engineers)
        if excluded_count:
            logger.info("単価REVIEW除外 %d件", excluded_count)
    _process_cases(cases, engineers, db, cost_guard, normalizer, notifier, notion=None, dry_run=True)
    db.recompute_daily_stats()
    notifier.flush(dry_run=True)


    notifier.flush(dry_run=True)


def _load_reprocess_today_case_ids(db: ProcessedDB) -> list[str]:
    with db._connect() as conn:
        rows = conn.execute(
            """
            SELECT case_id FROM processed_cases
            WHERE date(updated_at) = date('now', '+9 hours')
              AND business_status = 'matched'
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return [str(row["case_id"]) for row in rows]


def _load_structured_cache() -> dict[str, dict[str, Any]]:
    path = BASE_DIR / "logs" / "structured.jsonl"
    cache: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return cache
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            case_id = row.get("case_id")
            if case_id:
                cache[str(case_id)] = row
    return cache


def _fetch_notion_cases_for_reprocess(
    notion: NotionClient,
    case_ids: list[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for case_id in case_ids:
        try:
            page = notion._request("GET", f"pages/{case_id}")
            parsed = notion._parse_case_page(page)
            result[case_id] = parsed
        except Exception as exc:
            logger.warning("案件取得失敗 case_id=%s: %s", case_id, exc)
        time.sleep(0.3)
    return result


def _process_cases(
    cases: list[dict[str, Any]],
    engineers: list[dict[str, Any]],
    db: ProcessedDB,
    cost_guard: CostGuard,
    normalizer: SkillNormalizer,
    notifier: Notifier,
    notion: NotionClient | None,
    dry_run: bool,
    pending_by_target: dict[str, int] | None = None,
    reprocess_today: bool = False,
) -> dict[str, float | int]:
    pending_by_target = pending_by_target or {}

    def _mark_pending_done(case_id: str) -> None:
        queue_id = pending_by_target.get(case_id)
        if not queue_id:
            return
        try:
            from common.ledger import mark_pending_done

            mark_pending_done(queue_id)
        except Exception as exc:
            logger.error("pending_queue 完了更新エラー case=%s: %s", case_id, exc)
    started = time.perf_counter()
    engineers, staleness_excluded = partition_fresh_engineers(engineers, logger)
    total_engineers = staleness_excluded + len(engineers)
    if staleness_excluded:
        logger.info("鮮度フィルタ除外: %d / %d 名", staleness_excluded, total_engineers)
        db.record_staleness_excluded(staleness_excluded)

    engineers = [prepare_engineer_skills(engineer, normalizer) for engineer in engineers]
    skill_index = build_skill_index(engineers, normalizer)
    seen_case_ids: set[str] = set()
    skipped_cases = 0
    processed_cases = 0
    match_counts: list[int] = []
    mass_match_30plus = 0
    unmatchable_count = 0

    for case in cases:
        case_id = case["id"]
        if case_id in seen_case_ids:
            logger.info("duplicate case_id in input skipped: %s", case_id)
            continue
        seen_case_ids.add(case_id)

        last_edited = case.get("_last_edited_time") or case.get("last_edited_time") or ""
        if not reprocess_today and db.should_skip_unchanged_case(case_id, last_edited):
            skipped_cases += 1
            logger.info("skip unchanged case: %s", case_id)
            _mark_pending_done(case_id)
            continue

        body = case.get("案件詳細") or case.get("body") or ""
        if len(body) > 8000 and not reprocess_today:
            db.update_status(case_id, "SKIPPED", case_last_edited_at=last_edited or None)
            _mark_pending_done(case_id)
            continue

        cached_case_json = case.get("_cached_case_json")
        if reprocess_today:
            if cached_case_json:
                case_json = dict(cached_case_json)
                logger.info("reprocess-today: cached structurer使用 case=%s", case_id)
            else:
                case_json = {
                    "required_skills": [str(skill) for skill in (case.get("必要スキル") or [])],
                    "optional_skills": [str(skill) for skill in (case.get("尚可スキル") or [])],
                    "price_max": case.get("単価（万円）") or case.get("単価"),
                    "price_min": case.get("単価（万円）") or case.get("単価"),
                    "extraction_confidence": None,
                }
                logger.info("reprocess-today: notionのみで再構築 case=%s", case_id)
        elif not cached_case_json:
            if not cost_guard.can_call(len(body) // 4 + 200, 300, target_id=case_id):
                logger.warning("コスト上限到達: case_id=%s をpending_queueに登録", case_id)
                try:
                    from common.ledger import enqueue_pending, has_pending_target

                    if not has_pending_target(MATCHING_BATCH_PHASE, case_id):
                        enqueue_pending(
                            MATCHING_BATCH_PHASE,
                            block_type="matching_v3",
                            target_id=case_id,
                            script="matching_v3",
                        )
                except Exception as pq_err:
                    logger.error("pending_queue 登録エラー: %s", pq_err)
                continue

            db.mark_api_called(case_id, case.get("案件名", case.get("subject", "")), case.get("_created", ""))
            try:
                if dry_run and case.get("expected"):
                    case_json = case["expected"]
                else:
                    case_json = structurer.structure_case(case, body, cost_guard)
                    if case_json.get("extraction_retried"):
                        db.record_extraction_retry()
            except Exception as exc:
                logger.error("Structurer error: %s", exc)
                subject = case.get("案件名", case.get("subject", ""))
                case_json = structurer.rule_based_fallback(subject, body)
                if not structurer.is_recoverable(case_json):
                    db.increment_retry(case_id)
                    db.update_status(case_id, "ERROR")
                    continue
                logger.info("Structurer exception recovered via rule fallback: %s", case_id)

            if not dry_run:
                _save_to_jsonl(BASE_DIR / "logs" / "structured.jsonl", {"case_id": case_id, **case_json})
                db.update_status(case_id, "structured")

        case_for_notify = {**case, **case_json, "case_json": case_json}

        extracted_required = extract_raw_required_skills(case, case_json)
        required_skills, skills_source = resolve_case_required_skills(case, case_json, normalizer)
        case_json["required_skills"] = required_skills
        case_json["required_skills_source"] = skills_source
        case_json["extracted_required_skills"] = extracted_required
        case_json["normalized_technical_skills"] = required_skills

        matchable, unmatchable_status, unmatchable_reason, ng_reason = evaluate_matchability(
            case_json,
            extracted_required,
            required_skills,
        )
        if not matchable:
            unmatchable_count += 1
            logger.info(
                "UNMATCHABLE: case=%s status=%s reason=%s",
                case_id,
                unmatchable_status,
                unmatchable_reason,
            )
            unmatchable_results = [
                {
                    "unmatchable": True,
                    "status": unmatchable_status,
                    "reason": unmatchable_reason,
                    "ng_reason": ng_reason,
                }
            ]
            db.update_status(
                    case_id,
                    "ng",
                    unmatchable_results,
                    case_last_edited_at=last_edited or None,
                )
            if ng_reason == "ALL_REQUIRED_SKILLS_OOV":
                db.record_oov_skip()
            _mark_pending_done(case_id)
            processed_cases += 1
            match_counts.append(0)
            if dry_run:
                _save_to_jsonl(
                    BASE_DIR / "logs" / "phase0_results.jsonl",
                    {
                        "case_id": case_id,
                        "results": unmatchable_results,
                        "unmatchable_status": unmatchable_status,
                    },
                )
            continue

        if not required_skills and not extracted_required:
            logger.info("SKIPPED (no_required_skills): case=%s source=%s", case_id, skills_source)
            if not dry_run or reprocess_today:
                db.update_status(case_id, "SKIPPED", case_last_edited_at=last_edited or None)
            _mark_pending_done(case_id)
            continue

        if case_json.get("price_max") is None:
            notion_price = case.get("単価（万円）") or case.get("単価")
            if notion_price is not None:
                case_json["price_min"] = notion_price
                case_json["price_max"] = notion_price
        optional_skills = case.get("尚可スキル") or []
        if optional_skills and not case_json.get("optional_skills"):
            case_json["optional_skills"] = canonicalize_skill_list(
                [str(skill) for skill in optional_skills],
                normalizer,
            )
        case_for_notify = {**case, **case_json, "case_json": case_json}

        candidates, score_breakdowns, hard_stats = filter_candidates_3layer(
            engineers,
            case,
            case_json,
            normalizer,
            skill_index,
            required_skills,
        )
        logger.info(
            "3layer filter case=%s: engineers=%d -> candidates=%d (hard_drop proposal=%d active=%d late=%d)",
            case_id,
            len(engineers),
            len(candidates),
            hard_stats.dropped_proposal_flag,
            hard_stats.dropped_active_working,
            hard_stats.dropped_late_start,
        )
        if score_breakdowns:
            logger.debug("score_breakdowns case=%s count=%d", case_id, len(score_breakdowns))
        logger.info(
            "候補絞込 case=%s: %d -> %d (required=%d source=%s)",
            case_id,
            len(engineers),
            len(candidates),
            len(required_skills),
            skills_source,
        )
        log_case_skills_debug(case_id, required_skills, skills_source, logger=logger)

        def _judge_one(engineer: dict[str, Any]) -> dict[str, Any]:
            log_engineer_match_debug(engineer, logger=logger)
            staleness = staleness_check(engineer)
            judged = matcher.judge_with_meta(case_json, engineer, normalizer, case.get("担当者"))
            return {
                "engineer": engineer,
                "staleness": staleness,
                "judged": judged,
            }

        results: list[dict[str, Any]] = []
        judged_rows: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_judge_one, engineer) for engineer in candidates]
            for future in as_completed(futures):
                judged_rows.append(future.result())

        for row in judged_rows:
            engineer = row["engineer"]
            judged = row["judged"]
            verdict = judged["verdict"]
            reasons = judged["reasons"]
            score = float(judged.get("score", 0.0))
            staleness = row["staleness"]
            _save_match_result(case_for_notify, engineer, verdict, reasons, staleness, score=score)
            if verdict in ("MATCH", "REVIEW", "PARTIAL_MATCH"):
                results.append(
                    {
                        "engineer_id": engineer["id"],
                        "engineer_initial": _initial(engineer.get("名前", "")),
                        "verdict": verdict,
                        "reasons": reasons,
                        "process_requirements": judged.get("process_requirements", []),
                        "engineer_price": engineer.get("単価（万円）"),
                        "days_old": staleness.get("days_old"),
                        "profile_staleness_source": staleness.get("source_field"),
                        "score": score,
                    }
                )

        results.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        if len(results) > 20:
            logger.info("match count capped: case=%s %d -> 20", case_id, len(results))
            results = results[:20]

        match_counts.append(len(results))
        if len(results) > 30:
            mass_match_30plus += 1
            logger.warning("mass match: case=%s count=%d", case_id, len(results))

        if not results:
            try:
                from common.failure_collector import collect_failure

                ng_rows = [row for row in judged_rows if row["judged"]["verdict"] == "NG"]
                top_reasons = [row["judged"]["reasons"] for row in ng_rows[:3]]
                collect_failure(
                    "no_match",
                    {"case_id": case_id, "case_name": case.get("案件名"), "required_skills": required_skills},
                    str(top_reasons),
                )
            except Exception:
                pass

        final_status = "matched" if results else "ng"
        db.update_status(case_id, final_status, results, case_last_edited_at=last_edited or None)
        _mark_pending_done(case_id)
        processed_cases += 1
        if dry_run:
            _save_to_jsonl(BASE_DIR / "logs" / "phase0_results.jsonl", {"case_id": case_id, "results": results})
        elif notion:
            notion.update_match_status(case_id, results)

        for idx, result in enumerate(results):
            engineer = next((item for item in engineers if item["id"] == result["engineer_id"]), {})
            notifier.enqueue(
                case_for_notify,
                engineer,
                result["verdict"],
                result["reasons"],
                score=result.get("score"),
                priority=idx < 3,
            )

    elapsed = time.perf_counter() - started
    avg_matches = (sum(match_counts) / len(match_counts)) if match_counts else 0.0
    logger.info(
        "matching完了: 処理=%d スキップ=%d 入力=%d エンジニア=%d 所要=%.1fs unmatchable=%d mass30+=%d avg_matches=%.1f",
        processed_cases,
        skipped_cases,
        len(cases),
        len(engineers),
        elapsed,
        unmatchable_count,
        mass_match_30plus,
        avg_matches,
    )
    return {
        "processed_cases": processed_cases,
        "unmatchable_count": unmatchable_count,
        "mass_match_30plus": mass_match_30plus,
        "avg_matches": avg_matches,
    }


def _load_dry_input(input_path: str | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not input_path:
        raise ValueError("--input is required for --dry-run")
    path = Path(input_path)
    if not path.is_absolute():
        path = BASE_DIR / path
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if "case_examples" in data:
            cases = [
                {
                    "id": item["id"],
                    "案件名": item.get("subject", item["id"]),
                    "案件詳細": item["body"],
                    "担当者": "松野",
                    "expected": item.get("expected"),
                }
                for item in data["case_examples"]
            ]
            return cases, data.get("engineers", [])
        if isinstance(data, list):
            return data, []
    cases = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))
    return cases, []


def _save_to_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def _save_match_result(
    case: dict[str, Any],
    engineer: dict[str, Any],
    verdict: str,
    reasons: list[str],
    staleness: dict[str, Any] | None = None,
    *,
    score: float | None = None,
) -> None:
    payload = {
        "ts": datetime.now(JST).isoformat(),
        "case_id": case.get("id"),
        "case_name": case.get("案件名"),
        "verdict": verdict,
        "engineer_id": engineer.get("id"),
        "engineer_initial": _initial(engineer.get("名前", "")),
        "engineer_price": engineer.get("単価（万円）"),
        "reasons": reasons,
        "schema_version": "v1",
        "prompt_version": "v1",
    }
    if score is not None:
        payload["score"] = score
    if staleness is not None:
        payload["days_old"] = staleness.get("days_old")
        payload["profile_staleness_source"] = staleness.get("source_field")
    _save_to_jsonl(BASE_DIR / "logs" / "match_results.jsonl", payload)


def _is_business_day(target: date | None = None) -> bool:
    current = target or date.today()
    return current.weekday() < 5 and not jpholiday.is_holiday(current)


def _initial(name: str) -> str:
    parts = [part for part in name.replace("　", " ").split(" ") if part]
    if len(parts) >= 2:
        return ".".join(part[0].upper() for part in parts[:2])
    return name[:2] if name else ""


def _run_unknown_skill_discovery() -> None:
    try:
        from scripts.discover_unknown_skills import discover

        output = discover()
        if output:
            logger.info("unknown skill candidates: %s", output)
    except Exception as exc:
        logger.warning("unknown skill discovery skipped: %s", exc)


def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    # force=True: 単独起動時は matching_v3 ログを確実に設定する
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"matching_v3_{datetime.now(JST):%Y%m%d}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(logging.WARNING)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input")
    parser.add_argument(
        "--reprocess-today",
        action="store_true",
        help="本日のmatched案件をstructured.jsonlキャッシュで再マッチング（dry-run専用）",
    )
    parser.add_argument(
        "--recompute-stats",
        action="store_true",
        help="processed_cases から daily_stats を再集計（--stat-date 省略時は全期間）",
    )
    parser.add_argument("--stat-date", help="再集計対象日 (YYYY-MM-DD)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        _setup_logging()
    except Exception as _e:
        import traceback as _tb

        print(f"[FATAL] logging setup failed: {_e}", flush=True)
        _tb.print_exc()
        raise SystemExit(1)
    raise SystemExit(main())
