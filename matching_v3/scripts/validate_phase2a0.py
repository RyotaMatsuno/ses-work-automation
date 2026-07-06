"""
Phase 2A0 検証スクリプト
直近20案件でfilter_engineers_by_required_skillsのbefore/after avg_matchesを比較する。

実行方法:
  cd ses_work/matching_v3
  python scripts/validate_phase2a0.py [--dry-run]
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_HERE = Path(__file__).resolve().parent.parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from config import Config, MAX_CANDIDATES_BEFORE_JUDGE, SKILL_MATCH_THRESHOLD
from matcher import SkillNormalizer, build_skill_index, filter_engineers_by_required_skills, prepare_engineer_skills
from notion_client import NotionClient


def filter_and_count(
    engineers: list[dict],
    normalizer: SkillNormalizer,
    skill_index: dict,
    required_skills: list[str],
    *,
    threshold: float,
    cap: int,
) -> int:
    """閾値ベースの候補数を返す。"""
    if not required_skills:
        return len(engineers)
    resolved = [c for s in required_skills if (c := normalizer.resolve_canonical(s))]
    if not resolved:
        return 0
    counter: Counter[str] = Counter()
    for skill in resolved:
        for eid in skill_index.get(skill, set()):
            counter[eid] += 1
    min_match = max(1, math.ceil(threshold * len(resolved)))
    passing = [(eid, cnt) for eid, cnt in counter.items() if cnt >= min_match]
    return min(len(passing), cap)


def filter_and_count_and(
    engineers: list[dict],
    normalizer: SkillNormalizer,
    skill_index: dict,
    required_skills: list[str],
) -> int:
    """旧AND交差方式の候補数を返す（比較用）。"""
    if not required_skills:
        return len(engineers)
    candidate_ids: set[str] | None = None
    for skill in required_skills:
        canonical = normalizer.resolve_canonical(skill)
        if not canonical:
            continue
        skill_ids = skill_index.get(canonical, set())
        candidate_ids = skill_ids if candidate_ids is None else candidate_ids & skill_ids
    if candidate_ids is None:
        return 0
    return len(candidate_ids)


def main() -> None:
    cfg = Config()
    notion = NotionClient()
    normalizer = SkillNormalizer(_HERE / "skill_aliases.json")

    print("Notionからエンジニア取得中...")
    engineers = notion.get_proposal_target_engineers()
    engineers = [prepare_engineer_skills(engineer, normalizer) for engineer in engineers]
    print(f"  提案対象エンジニア: {len(engineers)}名")

    skill_index = build_skill_index(engineers, normalizer)

    print("Notionから直近20案件取得中...")
    cases = notion.get_active_cases(limit=20)
    print(f"  案件数: {len(cases)}")

    results = []
    for case in cases:
        case_id = case.get("id", "?")
        case_name = case.get("案件名", "?")
        required_raw = case.get("必要スキル") or []
        required = [s for s in required_raw if s]

        before = filter_and_count_and(engineers, normalizer, skill_index, required)
        after = len(
            filter_engineers_by_required_skills(
                engineers,
                normalizer,
                skill_index,
                required,
            )
        )
        results.append({
            "case_id": case_id,
            "case_name": case_name,
            "required_count": len(required),
            "before_candidates": before,
            "after_candidates": after,
        })
        print(f"  {case_name[:30]:30s} | required={len(required):2d} | before={before:3d} | after={after:3d}")

    avg_before = sum(r["before_candidates"] for r in results) / max(len(results), 1)
    avg_after = sum(r["after_candidates"] for r in results) / max(len(results), 1)

    print(f"\navg_matches before (AND): {avg_before:.2f}")
    print(f"avg_matches after  (50%): {avg_after:.2f}")
    print(f"目標: >= 3.0 ... {'OK' if avg_after >= 3.0 else 'NG'}")

    out_path = _HERE.parent / "research_results" / "phase2a0_validation.md"
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write("# Phase 2A0 Validation Results\n\n")
        f.write(f"- engineers: {len(engineers)}\n")
        f.write(f"- cases: {len(cases)}\n")
        f.write(f"- avg_before (AND): {avg_before:.2f}\n")
        f.write(f"- avg_after  (50%): {avg_after:.2f}\n")
        f.write(f"- threshold_pass: {'YES' if avg_after >= 3.0 else 'NO'}\n\n")
        f.write("| case | required | before | after |\n")
        f.write("|------|----------|--------|-------|\n")
        for r in results:
            f.write(f"| {r['case_name'][:40]} | {r['required_count']} | {r['before_candidates']} | {r['after_candidates']} |\n")
    print(f"\n結果保存: {out_path}")


if __name__ == "__main__":
    main()
