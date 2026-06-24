from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from attr_estimator import (
    build_notion_page_url,
    estimate_nationality,
    estimate_nationality_llm,
    extract_residence_from_memo,
)
from notion_client import (
    ENGINEER_DB_ID,
    RATE_LIMIT_SLEEP,
    REQUIRED_PROPERTIES,
    FlagNotionClient,
    NotionApiError,
)
from rule_engine import extract_prop

BASE_DIR = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)


def _setup_logging() -> Path:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"estimate_result_{datetime.now(JST):%Y%m%d}.txt"
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    return log_path


def _write_summary(
    log_path: Path,
    *,
    total: int,
    nationality_japan: int,
    nationality_foreign: int,
    nationality_review: int,
    residence_set: int,
    residence_unknown: int,
) -> None:
    lines = [
        f"推定完了: {total}件",
        f"国籍「日本」設定: {nationality_japan}件",
        f"国籍「外国籍候補」設定: {nationality_foreign}件",
        f"国籍「要確認」: {nationality_review}件（要確認リスト → estimate_needs_review.csv）",
        f"居住地設定: {residence_set}件",
        f"居住地不明（空欄のまま）: {residence_unknown}件",
    ]
    for line in lines:
        logger.info(line)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _write_review_csv(review_rows: list[dict[str, str]]) -> Path:
    csv_path = BASE_DIR / "logs" / "estimate_needs_review.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["氏名", "NotionURL", "推定根拠"])
        writer.writeheader()
        writer.writerows(review_rows)
    return csv_path


def run_estimate_engineer_attrs(*, dry_run: bool = False) -> int:
    log_path = _setup_logging()
    mode = "ドライラン" if dry_run else "本番"
    logger.info("エンジニア属性推定を開始 (%s)", mode)

    try:
        client = FlagNotionClient()
    except ValueError as exc:
        logger.error("初期化失敗: %s", exc)
        return 1

    try:
        client.ensure_properties(ENGINEER_DB_ID, REQUIRED_PROPERTIES)
        engineers = client.get_all_engineers(ENGINEER_DB_ID)
    except NotionApiError as exc:
        if exc.status_code == 401:
            logger.error("Notion API 401 のため処理を中断: %s", exc)
            return 1
        logger.error("Notion取得エラー: %s", exc)
        return 1

    stats = {
        "nationality_japan": 0,
        "nationality_foreign": 0,
        "nationality_review": 0,
        "residence_set": 0,
        "residence_unknown": 0,
    }
    review_rows: list[dict[str, str]] = []
    update_errors = 0

    for index, engineer in enumerate(engineers, start=1):
        page_id = engineer.get("id", "")
        name = engineer.get("名前", "")
        memo = engineer.get("備考（LINEメモ）", "")
        current_nationality = extract_prop(engineer, "国籍", "select")
        current_residence = extract_prop(engineer, "居住地", "select")

        nationality_to_set: str | None = None
        residence_to_set: str | None = None
        reasons: list[str] = []

        if not current_nationality:
            nationality_to_set, nationality_reason = estimate_nationality(name, memo)

            if nationality_to_set == "要確認":
                llm_value, llm_reason = estimate_nationality_llm(name, memo)
                logger.info(
                    "[LLM判定] %s | %s → %s (%s)",
                    name or page_id,
                    nationality_reason,
                    llm_value,
                    llm_reason,
                )
                nationality_reason = llm_reason
                if llm_value == "要確認":
                    nationality_to_set = None
                    stats["nationality_review"] += 1
                    review_rows.append(
                        {
                            "氏名": name,
                            "NotionURL": build_notion_page_url(page_id),
                            "推定根拠": nationality_reason,
                        }
                    )
                else:
                    nationality_to_set = llm_value
                    if llm_value == "日本":
                        stats["nationality_japan"] += 1
                    else:
                        stats["nationality_foreign"] += 1
            elif nationality_to_set == "日本":
                stats["nationality_japan"] += 1
            elif nationality_to_set == "外国籍候補":
                stats["nationality_foreign"] += 1

            if nationality_to_set:
                reasons.append(f"国籍={nationality_to_set}: {nationality_reason}")

        if not current_residence:
            residence_to_set, residence_reason = extract_residence_from_memo(memo)
            if residence_to_set:
                stats["residence_set"] += 1
                reasons.append(f"居住地={residence_to_set}: {residence_reason}")
            else:
                stats["residence_unknown"] += 1

        if not nationality_to_set and not residence_to_set:
            continue

        if dry_run:
            logger.info(
                "[DRY-RUN] %s | %s",
                name or page_id,
                " / ".join(reasons),
            )
            continue

        try:
            client.update_engineer_attributes(
                page_id,
                nationality=nationality_to_set,
                residence=residence_to_set,
            )
        except NotionApiError as exc:
            update_errors += 1
            logger.warning(
                "更新失敗 page_id=%s name=%s: %s",
                page_id,
                name,
                exc,
            )
        time.sleep(RATE_LIMIT_SLEEP)
        if len(engineers) > 100 and index % 10 == 0:
            time.sleep(1)

    _write_summary(
        log_path,
        total=len(engineers),
        nationality_japan=stats["nationality_japan"],
        nationality_foreign=stats["nationality_foreign"],
        nationality_review=stats["nationality_review"],
        residence_set=stats["residence_set"],
        residence_unknown=stats["residence_unknown"],
    )

    if review_rows:
        csv_path = _write_review_csv(review_rows)
        logger.info("要確認リスト: %s", csv_path)

    if update_errors and update_errors == len(engineers):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="エンジニアの国籍・居住地を自動推定してNotionに反映")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Notionへの書き込みを行わず、ログのみ出力",
    )
    args = parser.parse_args()
    return run_estimate_engineer_attrs(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
