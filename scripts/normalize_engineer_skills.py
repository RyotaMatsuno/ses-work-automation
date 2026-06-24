#!/usr/bin/env python3
"""Task AK: エンジニアDBのスキルを skill_aliases.json でcanonical化するバッチ。

Usage (ses_work ルートから):
    python scripts/normalize_engineer_skills.py --dry-run  # プレビューのみ
    python scripts/normalize_engineer_skills.py              # 正規化スキルフィールドへ書き込み

注意: 生の「スキル」プロパティは上書きしない。「正規化スキル」フィールドに保存する。
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SES_WORK = Path(__file__).resolve().parent.parent
MATCHING_V3 = SES_WORK / "matching_v3"
for _p in (str(MATCHING_V3), str(SES_WORK)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from matcher import SkillNormalizer  # noqa: E402
from notion_client import NotionClient  # noqa: E402

ALIASES_PATH = MATCHING_V3 / "skill_aliases.json"
LOG_PATH = MATCHING_V3 / "logs" / "normalize_engineer_skills.jsonl"

logger = logging.getLogger(__name__)


def normalize_skills(raw_skills: list[str], normalizer: SkillNormalizer) -> tuple[list[str], list[dict]]:
    """各生スキルを canonical 化し、重複除去済みリストとマッピングを返す。"""
    mapping: list[dict] = []
    canonical: list[str] = []
    seen: set[str] = set()
    for raw in raw_skills:
        hard = normalizer.normalize_hard(raw)
        soft = normalizer.normalize_soft(raw) if not hard else None
        target = hard or soft
        mapping.append({"raw": raw, "canonical": target})
        resolved = target if target else raw.strip()
        if resolved and resolved not in seen:
            seen.add(resolved)
            canonical.append(resolved)
    return canonical, mapping


def coverage_stats(all_raw: list[str], normalizer: SkillNormalizer) -> dict:
    """全スキル語彙のうち辞書でカバーされた割合を計算する。"""
    unique_raw = list(dict.fromkeys(all_raw))
    if not unique_raw:
        return {"total": 0, "covered": 0, "coverage_pct": 0.0}
    covered = sum(
        1 for s in unique_raw if normalizer.normalize_hard(s) or normalizer.normalize_soft(s)
    )
    total = len(unique_raw)
    return {
        "total": total,
        "covered": covered,
        "coverage_pct": round(covered / total * 100, 1),
    }


def run(*, dry_run: bool) -> dict:
    normalizer = SkillNormalizer(ALIASES_PATH)
    client = NotionClient()
    engineers = client.get_all_engineers()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    changed = 0
    unchanged = 0
    error_count = 0
    all_raw_tokens: list[str] = []

    with LOG_PATH.open("w", encoding="utf-8") as log_f:
        for eng in engineers:
            raw = [str(s) for s in (eng.get("スキル") or [])]
            if not raw:
                unchanged += 1
                continue

            all_raw_tokens.extend(raw)
            canonical, mapping = normalize_skills(raw, normalizer)
            changed_pairs = [m for m in mapping if m["canonical"] and m["raw"] != m["canonical"]]

            if not changed_pairs and canonical == [s.strip() for s in raw if s.strip()]:
                unchanged += 1
                continue

            changed += 1
            name = eng.get("名前") or eng.get("id")
            for pair in changed_pairs:
                logger.info("[変更] %s: %r → %r", name, pair["raw"], pair["canonical"])

            entry = {
                "engineer_id": eng.get("id"),
                "name": name,
                "raw_skills": raw,
                "canonical_skills": canonical,
                "mapping": mapping,
                "dry_run": dry_run,
            }
            log_f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            if not dry_run:
                ok = client.update_engineer_normalized_skills(str(eng.get("id")), canonical)
                if ok:
                    logger.info("[更新完了] %s (%d スキル)", name, len(canonical))
                else:
                    error_count += 1
                    logger.warning("[更新失敗] %s — 正規化スキルフィールドが未作成の可能性", name)

    stats = coverage_stats(all_raw_tokens, normalizer)
    logger.info("=== 正規化サマリー ===")
    logger.info("取得エンジニア数: %d", len(engineers))
    logger.info("変更あり: %d名 / 変更なし: %d名 / エラー: %d名", changed, unchanged, error_count)
    logger.info(
        "正規化カバレッジ: %.1f%% (%d / %d ユニーク語彙)",
        stats["coverage_pct"],
        stats["covered"],
        stats["total"],
    )
    logger.info("ログ: %s", LOG_PATH)
    if dry_run:
        logger.info("[dry-run] Notion への書き込みはスキップしました")

    return {
        "engineers": len(engineers),
        "changed": changed,
        "unchanged": unchanged,
        "errors": error_count,
        **stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="エンジニアDBのスキルをcanonical化する")
    parser.add_argument("--dry-run", action="store_true", help="変更内容をプレビュー（Notion更新なし）")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    run(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
