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
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jpholiday

import matcher
import structurer
from config import Config
from cost_guard import CostGuard
from matcher import SkillNormalizer, filter_fresh_engineers
from notion_client import NotionClient
from notifier import Notifier
from processed_db import ProcessedDB


BASE_DIR = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)


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
    if not _is_business_day():
        logger.info("非稼働日のためスキップ")
        return 0

    lock = LockFile(BASE_DIR / "matching_v3.lock")
    if not lock.acquire():
        logger.warning("別プロセスが実行中")
        return 0

    try:
        if args.dry_run:
            _run_dry(args.input)
        else:
            _run_live()
    finally:
        lock.release()
    return 0


def _run_live() -> None:
    db = ProcessedDB()
    cost_guard = CostGuard()
    notifier = Notifier()
    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")
    notion = NotionClient()

    cases = notion.get_new_cases(days=4)
    engineers = notion.get_active_engineers()
    _process_cases(cases, engineers, db, cost_guard, normalizer, notifier, notion=notion, dry_run=False)
    notifier.flush()


def _run_dry(input_path: str | None) -> None:
    db = ProcessedDB(BASE_DIR / "logs" / "phase0_processed.db")
    cost_guard = CostGuard(BASE_DIR / "logs" / "phase0_cost_log.jsonl")
    notifier = Notifier(Config())
    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")
    cases, engineers = _load_dry_input(input_path)
    if not engineers:
        # JSONL入力の場合はNotionから実エンジニアを取得（Phase0精度評価に必要）
        notion_client = NotionClient(Config())
        engineers = notion_client.get_active_engineers()
        logger.info("dry-run: fetched %d engineers from Notion", len(engineers))
    else:
        engineers = filter_fresh_engineers(engineers, logger)
    _process_cases(cases, engineers, db, cost_guard, normalizer, notifier, notion=None, dry_run=True)
    notifier.flush(dry_run=True)


def _process_cases(
    cases: list[dict[str, Any]],
    engineers: list[dict[str, Any]],
    db: ProcessedDB,
    cost_guard: CostGuard,
    normalizer: SkillNormalizer,
    notifier: Notifier,
    notion: NotionClient | None,
    dry_run: bool,
) -> None:
    seen_case_ids: set[str] = set()
    for case in cases:
        case_id = case["id"]
        if case_id in seen_case_ids:
            logger.info("duplicate case_id in input skipped: %s", case_id)
            continue
        seen_case_ids.add(case_id)
        if db.is_processed(case_id):
            continue

        body = case.get("案件詳細") or case.get("body") or ""
        if len(body) > 8000:
            db.update_status(case_id, "SKIPPED")
            continue
        if not cost_guard.can_call(len(body) // 4 + 200, 300):
            logger.warning("コスト上限到達、処理停止")
            break

        db.mark_api_called(case_id, case.get("案件名", case.get("subject", "")), case.get("_created", ""))
        try:
            if dry_run and case.get("expected"):
                case_json = case["expected"]
            else:
                case_json = structurer.structure(body, cost_guard)
        except Exception as exc:
            logger.error("Structurer error: %s", exc)
            db.update_status(case_id, "ERROR")
            continue

        case_for_notify = {**case, **case_json, "case_json": case_json}
        _save_to_jsonl(BASE_DIR / "logs" / "structured.jsonl", {"case_id": case_id, **case_json})
        db.update_status(case_id, "structured")

        results = []
        for engineer in engineers:
            verdict, reasons = matcher.judge(case_json, engineer, normalizer, case.get("担当者"))
            _save_match_result(case_for_notify, engineer, verdict, reasons)
            if verdict in ("MATCH", "REVIEW"):
                results.append(
                    {
                        "engineer_id": engineer["id"],
                        "engineer_initial": _initial(engineer.get("名前", "")),
                        "verdict": verdict,
                        "reasons": reasons,
                        "engineer_price": engineer.get("単価（万円）"),
                    }
                )

        db.update_status(case_id, "matched", results)
        if dry_run:
            _save_to_jsonl(BASE_DIR / "logs" / "phase0_results.jsonl", {"case_id": case_id, "results": results})
        elif notion:
            notion.update_match_status(case_id, results)

        for result in results:
            engineer = next((item for item in engineers if item["id"] == result["engineer_id"]), {})
            notifier.enqueue(case_for_notify, engineer, result["verdict"], result["reasons"])


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


def _save_match_result(case: dict[str, Any], engineer: dict[str, Any], verdict: str, reasons: list[str]) -> None:
    _save_to_jsonl(
        BASE_DIR / "logs" / "match_results.jsonl",
        {
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
        },
    )


def _is_business_day(target: date | None = None) -> bool:
    current = target or date.today()
    return current.weekday() < 5 and not jpholiday.is_holiday(current)


def _initial(name: str) -> str:
    parts = [part for part in name.replace("　", " ").split(" ") if part]
    if len(parts) >= 2:
        return ".".join(part[0].upper() for part in parts[:2])
    return name[:2] if name else ""


def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / f"matching_v3_{datetime.now(JST):%Y%m%d}.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(logging.WARNING)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--input")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
