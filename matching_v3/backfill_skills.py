"""スキル空レコードにスキルを再抽出してNotionへバックフィルするスクリプト。

対象: ステータス=募集中 かつ 必要スキル=空 かつ 案件情報原文≠空

Usage:
    python backfill_skills.py              # dry-run
    python backfill_skills.py --execute    # 本番実行
"""
from __future__ import annotations

import argparse
import logging
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _jst_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=9)))


def run_backfill(execute: bool = False, conservative: bool = True) -> dict[str, Any]:
    from mail_pipeline.skill_extractor import extract_skills, load_skill_aliases
    from config import CASE_DB_ID, Config
    from notion_client import NotionClient

    config = Config()
    notion = NotionClient(config)
    alias_values = set(load_skill_aliases().values())

    def _allowed(skills: list[str]) -> list[str]:
        if not conservative:
            return skills
        return [s for s in skills if s in alias_values]

    payload = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
            ]
        }
    }
    pages = notion._query_database(CASE_DB_ID, payload)
    logger.info("募集中案件: %d件", len(pages))

    stats = {
        "total": len(pages),
        "target": 0,
        "filled": 0,
        "no_extract": 0,
        "failed": 0,
        "filtered_out": 0,
        "execute": execute,
        "conservative": conservative,
    }
    samples: list[dict[str, Any]] = []

    for page in pages:
        page_id = page.get("id", "")
        props = page.get("properties", {})

        skill_prop = props.get("必要スキル") or {}
        existing_skills = [
            opt.get("name", "") for opt in (skill_prop.get("multi_select") or []) if opt.get("name")
        ]
        if existing_skills:
            continue

        original_prop = props.get("案件情報原文") or {}
        rich_text = original_prop.get("rich_text") or []
        body = "".join(rt.get("plain_text", "") for rt in rich_text).strip()
        if not body:
            continue

        stats["target"] += 1
        subject_prop = props.get("案件名") or {}
        title_items = subject_prop.get("title") or []
        subject = "".join(t.get("plain_text", "") for t in title_items).strip()

        result = extract_skills(subject, body)
        required = _allowed(result.get("required", []))
        optional = _allowed(result.get("optional", []))
        raw_count = len(result.get("required", [])) + len(result.get("optional", []))
        stats["filtered_out"] += max(0, raw_count - len(required) - len(optional))
        if not required and not optional:
            stats["no_extract"] += 1
            logger.info("抽出0件: page_id=%s subject=%s", page_id, subject[:40])
            continue

        logger.info(
            "抽出: page_id=%s required=%s optional=%s (%s)",
            page_id,
            required,
            optional,
            "本番" if execute else "dry-run",
        )
        if len(samples) < 30:
            samples.append(
                {
                    "page_id": page_id,
                    "subject": subject[:60],
                    "required": required[:10],
                    "optional": optional[:10],
                }
            )
        if execute:
            properties: dict[str, Any] = {}
            if required:
                properties["必要スキル"] = {"multi_select": [{"name": s} for s in required[:10]]}
            if optional:
                properties["尚可スキル"] = {"multi_select": [{"name": s} for s in optional[:10]]}
            if not properties:
                stats["no_extract"] += 1
                continue
            ok = notion._patch_page_with_rate_limit(page_id, properties)
            if ok:
                stats["filled"] += 1
            else:
                stats["failed"] += 1
            time.sleep(0.4)
        else:
            stats["filled"] += 1

    report_path = RESULTS_DIR / f"backfill_skills_dryrun_{_jst_now():%Y%m%d}.md"
    _write_report(report_path, stats, samples)
    logger.info("レポート出力: %s", report_path)
    return stats


def _write_report(path: Path, stats: dict[str, Any], samples: list[dict[str, Any]]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    mode = "本番実行" if stats.get("execute") else "dry-run"
    lines = [
        f"# スキルバックフィルレポート ({mode})",
        "",
        "## 集計",
        f"- 募集中案件数: {stats['total']}",
        f"- 対象（スキル空+原文あり）: {stats['target']}",
        f"- 抽出成功: {stats['filled']}",
        f"- 抽出0件: {stats['no_extract']}",
        f"- 更新失敗: {stats['failed']}",
        "",
        "## 抽出サンプル（最大30件）",
    ]
    for item in samples:
        lines.append(
            f"- `{item['subject']}` → required={item.get('required', item.get('skills', []))} "
            f"optional={item.get('optional', [])} (page_id={item['page_id'][:8]}...)"
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="スキル空案件バックフィル")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    stats = run_backfill(execute=args.execute)
    logger.info("完了: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
