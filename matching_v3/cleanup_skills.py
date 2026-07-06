"""Notion案件DBの必要スキルmulti_selectからゴミ値を除去するスクリプト。

Usage:
    python cleanup_skills.py               # dry-run (デフォルト)
    python cleanup_skills.py --execute     # 本番実行（ゴミ値をNotionから除去）
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from script_bootstrap import bootstrap

BASE_DIR, SES_WORK = bootstrap()
RESULTS_DIR = SES_WORK / "research_results"
JST_OFFSET = 9 * 3600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _jst_now() -> datetime:
    from datetime import timezone as tz, timedelta
    return datetime.now(tz(timedelta(hours=9)))


def run_cleanup(execute: bool = False) -> dict[str, Any]:
    from mail_pipeline.skill_extractor import SKILL_ALIASES, validate_skill
    from config import CASE_DB_ID, Config
    from notion_client import NotionClient

    config = Config()
    notion = NotionClient(config)

    logger.info("案件DB全件取得中...")
    pages = notion._query_database(CASE_DB_ID, {})
    logger.info("取得: %d件", len(pages))

    valid_alias_keys = {k.lower() for k in SKILL_ALIASES}

    stats = {
        "total_pages": len(pages),
        "pages_with_skills": 0,
        "canonical_count": 0,
        "garbage_count": 0,
        "review_count": 0,
        "pages_updated": 0,
        "pages_failed": 0,
    }
    garbage_samples: list[str] = []
    review_samples: list[str] = []

    backup_path = RESULTS_DIR / f"skill_cleanup_backup_{_jst_now():%Y%m%d_%H%M%S}.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    backup_data: list[dict[str, Any]] = []

    for page in pages:
        page_id = page.get("id", "")
        props = page.get("properties", {})
        skill_prop = props.get("必要スキル") or {}
        raw_options = skill_prop.get("multi_select") or []
        skill_names = [opt.get("name", "") for opt in raw_options if opt.get("name")]
        if not skill_names:
            continue

        stats["pages_with_skills"] += 1
        backup_data.append({"page_id": page_id, "skills": skill_names})

        canonical: list[str] = []
        garbage: list[str] = []
        review: list[str] = []

        for name in skill_names:
            if name.lower() in valid_alias_keys:
                canonical.append(name)
            elif not validate_skill(name)[0]:
                garbage.append(name)
                if len(garbage_samples) < 30:
                    garbage_samples.append(name)
            else:
                review.append(name)
                if len(review_samples) < 30:
                    review_samples.append(name)

        stats["canonical_count"] += len(canonical)
        stats["garbage_count"] += len(garbage)
        stats["review_count"] += len(review)

        if execute and garbage:
            kept = [name for name in skill_names if name not in garbage]
            properties = {
                "必要スキル": {
                    "multi_select": [{"name": s} for s in kept]
                }
            }
            ok = notion._patch_page_with_rate_limit(page_id, properties)
            if ok:
                stats["pages_updated"] += 1
                logger.info("更新完了: page_id=%s removed=%d", page_id, len(garbage))
            else:
                stats["pages_failed"] += 1
                logger.warning("更新失敗: page_id=%s", page_id)
            time.sleep(0.4)

    with backup_path.open("w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    logger.info("バックアップ保存: %s", backup_path)

    report_path = RESULTS_DIR / f"skill_cleanup_dryrun_{_jst_now():%Y%m%d}.md"
    _write_report(report_path, stats, garbage_samples, review_samples, execute=execute)
    logger.info("レポート出力: %s", report_path)
    return stats


def _write_report(
    path: Path,
    stats: dict[str, Any],
    garbage_samples: list[str],
    review_samples: list[str],
    *,
    execute: bool,
) -> None:
    mode = "本番実行" if execute else "dry-run"
    lines = [
        f"# スキルクリーンアップレポート ({mode})",
        f"",
        f"## 集計",
        f"- 対象案件数: {stats['total_pages']}",
        f"- スキル有り案件: {stats['pages_with_skills']}",
        f"- canonical（保持）: {stats['canonical_count']}",
        f"- garbage（削除対象）: {stats['garbage_count']}",
        f"- review（手動確認）: {stats['review_count']}",
    ]
    if execute:
        lines += [
            f"- 更新成功: {stats['pages_updated']}",
            f"- 更新失敗: {stats['pages_failed']}",
        ]
    lines += [
        f"",
        f"## ゴミサンプル（最大30件）",
    ]
    for s in garbage_samples:
        lines.append(f"- `{s}`")
    lines += [
        f"",
        f"## 要確認サンプル（最大30件）",
    ]
    for s in review_samples:
        lines.append(f"- `{s}`")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Notionスキルゴミ除去")
    parser.add_argument("--execute", action="store_true", help="実行モード（省略時はdry-run）")
    args = parser.parse_args()

    stats = run_cleanup(execute=args.execute)
    logger.info("完了: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
