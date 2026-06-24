from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from .notion_client import (
    ENGINEER_DB_ID,
    RATE_LIMIT_SLEEP,
    REQUIRED_PROPERTIES,
    FlagNotionClient,
    NotionApiError,
)
from .rule_engine import format_reasons, judge_engineer

BASE_DIR = Path(__file__).resolve().parent
JST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"flag_updater_{datetime.now(JST):%Y%m%d}.log"

    root_logger = logging.getLogger()

    # 既にハンドラーが設定済み（親プロセスのlogging設定が生きている）場合は
    # flag_updater 専用のファイルハンドラーだけ追加する（force上書きしない）
    if root_logger.handlers:
        existing_paths = [
            getattr(h, "baseFilename", None) for h in root_logger.handlers if isinstance(h, logging.FileHandler)
        ]
        if str(log_path) not in existing_paths:
            flag_handler = logging.FileHandler(log_path, encoding="utf-8")
            flag_handler.setLevel(logging.INFO)
            flag_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
            root_logger.addHandler(flag_handler)
        return

    # 単独起動時（ハンドラーなし）は従来通り basicConfig で設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_flag_updater() -> int:
    _setup_logging()
    logger.info("提案対象フラグ自動更新を開始")

    try:
        client = FlagNotionClient()
    except ValueError as exc:
        logger.error("初期化失敗: %s", exc)
        return 1

    try:
        schema = client.get_database_schema(ENGINEER_DB_ID)
        logger.info("DBプロパティ数: %d", len(schema))
        client.ensure_properties(ENGINEER_DB_ID, REQUIRED_PROPERTIES)
        engineers = client.get_all_engineers(ENGINEER_DB_ID)
    except NotionApiError as exc:
        if exc.status_code == 401:
            logger.error("Notion API 401 のため処理を中断: %s", exc)
            return 1
        logger.error("Notion取得エラー: %s", exc)
        return 1

    logger.info("エンジニア取得件数: %d", len(engineers))

    targets: list[dict] = []
    excluded: list[dict] = []
    update_errors = 0

    for index, engineer in enumerate(engineers, start=1):
        is_target, reasons = judge_engineer(engineer)
        reason_text = format_reasons(reasons)
        record = {
            "id": engineer["id"],
            "名前": engineer.get("名前", ""),
            "is_target": is_target,
            "reasons": reasons,
        }
        if is_target:
            targets.append(record)
        else:
            excluded.append(record)

        try:
            client.update_engineer_flag(engineer["id"], is_target, reason_text)
        except NotionApiError as exc:
            update_errors += 1
            logger.warning(
                "更新失敗 page_id=%s name=%s: %s",
                engineer.get("id"),
                engineer.get("名前"),
                exc,
            )
        time.sleep(RATE_LIMIT_SLEEP)
        if len(engineers) > 100 and index % 10 == 0:
            time.sleep(1)

    logger.info("=== サマリー ===")
    logger.info("総件数: %d", len(engineers))
    logger.info("対象件数: %d", len(targets))
    logger.info("除外件数: %d", len(excluded))
    logger.info("更新失敗: %d", update_errors)
    if excluded:
        logger.info("--- 除外者一覧 ---")
        for item in excluded:
            logger.info(
                "  %s | %s",
                item.get("名前") or item.get("id"),
                format_reasons(item.get("reasons", [])),
            )

    if update_errors and update_errors == len(engineers):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_flag_updater())
