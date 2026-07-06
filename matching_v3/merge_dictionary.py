"""Phase 2: auto_classify結果を skill_aliases.json にマージする。

Usage:
    python matching_v3/merge_dictionary.py
    python matching_v3/merge_dictionary.py --execute
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from script_bootstrap import bootstrap

BASE_DIR, SES_WORK = bootstrap()
RESULTS_DIR = SES_WORK / "research_results"
ALIASES_PATH = BASE_DIR / "skill_aliases.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MANUAL_ALIASES: dict[str, str] = {
    "c言語": "C",
    "c language": "C",
    "windows os": "Windows",
    "windows os知識": "Windows",
    "ut": "単体テスト",
    "unit test": "単体テスト",
    "c/c++": "C/C++",
    "shell": "Shell",
    "シェル": "Shell",
    "golang": "Go",
    "vba": "VBA",
    "excel vba": "VBA",
    "access": "Access",
    "pl/sql": "PL/SQL",
    "llm": "LLM",
    "リーダー経験": "リーダー",
    "nw設計": "ネットワーク設計",
    "web開発": "Web開発",
    "skysea": "SKYSEA",
    "firewall": "Firewall",
    "fw": "Firewall",
}


def _latest(path_glob: str) -> Path | None:
    files = sorted(RESULTS_DIR.glob(path_glob))
    return files[-1] if files else None


def run(execute: bool = False) -> dict[str, Any]:
    candidates_path = _latest("skill_add_candidates_*.json")
    review_path = _latest("skill_review_queue_*.json")
    if not candidates_path:
        logger.error("skill_add_candidates_*.json not found")
        sys.exit(1)

    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    aliases: dict[str, str] = dict(data.get("aliases", {}))
    canonical: list[str] = list(data.get("canonical_skills", []))
    canonical_lower = {c.lower() for c in canonical}

    stats = {
        "auto_merged": 0,
        "review_merged": 0,
        "manual_merged": 0,
        "skipped_low_confidence": 0,
        "skipped_review_queue": 0,
    }

    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    for item in candidates:
        conf = float(item.get("confidence", 0))
        cls = item.get("class", "")
        form = item.get("canonical_form")
        skill = item.get("skill", "")
        if not form or cls not in ("tech_skill", "role", "process"):
            stats["skipped_low_confidence"] += 1
            continue
        if conf >= 0.95:
            key = str(skill).lower().strip()
            aliases[key] = str(form)
            if form.lower() not in canonical_lower:
                canonical.append(str(form))
                canonical_lower.add(form.lower())
            stats["auto_merged"] += 1
        elif conf >= 0.80:
            stats["skipped_review_queue"] += 1
        else:
            stats["skipped_low_confidence"] += 1

    if review_path:
        review_items = json.loads(review_path.read_text(encoding="utf-8"))
        for item in review_items:
            conf = float(item.get("confidence", 0))
            cls = item.get("class", "")
            form = item.get("canonical_form")
            skill = item.get("skill", "")
            if conf >= 0.5 and cls in ("role", "process") and form:
                key = str(skill).lower().strip()
                aliases[key] = str(form)
                if form.lower() not in canonical_lower:
                    canonical.append(str(form))
                    canonical_lower.add(form.lower())
                stats["review_merged"] += 1
            else:
                stats["skipped_review_queue"] += 1

    for key, form in MANUAL_ALIASES.items():
        aliases[key] = form
        if form.lower() not in canonical_lower:
            canonical.append(form)
            canonical_lower.add(form.lower())
        stats["manual_merged"] += 1

    canonical = sorted(set(canonical), key=lambda x: x.lower())
    report = {
        "date": date.today().isoformat(),
        "execute": execute,
        "stats": stats,
        "canonical_count": len(canonical),
        "alias_count": len(aliases),
    }

    today = date.today().strftime("%Y%m%d")
    report_path = RESULTS_DIR / f"skill_merge_report_{today}.md"
    RESULTS_DIR.mkdir(exist_ok=True)
    lines = [
        f"# 辞書マージレポート {today}",
        "",
        f"- 自動マージ (conf>=0.95): {stats['auto_merged']}",
        f"- レビューキューからマージ: {stats['review_merged']}",
        f"- 手動エントリ: {stats['manual_merged']}",
        f"- スキップ (低confidence): {stats['skipped_low_confidence']}",
        f"- スキップ (review待ち): {stats['skipped_review_queue']}",
        f"- canonical数: {len(canonical)}",
        f"- alias数: {len(aliases)}",
        f"- 実行モード: {'execute' if execute else 'dry-run'}",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("レポート: %s", report_path)

    if execute:
        data["canonical_skills"] = canonical
        data["aliases"] = dict(sorted(aliases.items(), key=lambda x: x[0].lower()))
        data["generated"] = date.today().isoformat()
        data["source"] = data.get("source", "") + " + merge_dictionary R3"
        ALIASES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("skill_aliases.json 更新完了")
        load_skill_aliases = None  # noqa: F841
        try:
            from mail_pipeline.skill_extractor import load_skill_aliases as _lsa

            _lsa.cache_clear()
        except Exception:
            pass

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="辞書マージ")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = run(execute=args.execute)
    logger.info("完了: %s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
