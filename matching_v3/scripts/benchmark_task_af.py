"""Task AF: estimate REVIEW->MATCH transitions on 6/23 matched cases."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from matcher import SkillNormalizer, _is_capability_skill

NON_VOCAB_REVIEW_PREFIXES = (
    "案件単価推定",
    "エンジニア単価推定",
    "エンジニア情報古い",
    "曖昧スキルあり",
    "構造化精度低",
    "並行過多",
)


def _load_structured() -> dict[str, dict]:
    cases: dict[str, dict] = {}
    path = BASE / "logs" / "structured.jsonl"
    if not path.exists():
        return cases
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            cases[row["case_id"]] = row
    return cases


def _extract_unknown_skills(reasons: list[str]) -> list[str]:
    skills: list[str] = []
    for reason in reasons:
        if not reason.startswith("語彙外必須スキル要確認:"):
            continue
        part = reason.split(":", 1)[1].strip()
        skills.extend(skill.strip() for skill in part.split(","))
    return skills


def _resolve_unknown(skill: str, normalizer: SkillNormalizer) -> bool:
    if _is_capability_skill(skill):
        return True
    return normalizer.normalize_hard(skill) is not None


def _has_other_review_reasons(reasons: list[str]) -> bool:
    for reason in reasons:
        if reason.startswith("語彙外必須スキル要確認"):
            continue
        if any(reason.startswith(prefix) for prefix in NON_VOCAB_REVIEW_PREFIXES):
            return True
    return False


def main() -> None:
    conn = sqlite3.connect(BASE / "matching_v3_processed.db")
    matched_case_ids = {
        row[0]
        for row in conn.execute(
            "SELECT case_id FROM processed_cases WHERE date(updated_at)='2026-06-23' AND business_status='matched'"
        )
    }
    conn.close()

    normalizer = SkillNormalizer(BASE / "skill_aliases.json")
    structured = _load_structured()

    total_rows = 0
    review_rows = 0
    match_rows = 0
    ng_rows = 0
    vocab_review_rows = 0
    vocab_only_review_rows = 0
    would_match_rows = 0

    with (BASE / "logs" / "match_results.jsonl").open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if not row["ts"].startswith("2026-06-23"):
                continue
            if row["case_id"] not in matched_case_ids:
                continue

            total_rows += 1
            verdict = row["verdict"]
            reasons = row.get("reasons", [])

            if verdict == "MATCH":
                match_rows += 1
            elif verdict == "NG":
                ng_rows += 1
            elif verdict == "REVIEW":
                review_rows += 1
                unknowns = _extract_unknown_skills(reasons)
                if not unknowns:
                    continue
                vocab_review_rows += 1
                if not _has_other_review_reasons(reasons):
                    vocab_only_review_rows += 1
                    if all(_resolve_unknown(skill, normalizer) for skill in unknowns):
                        would_match_rows += 1

    projected_match = match_rows + would_match_rows
    projected_review = review_rows - would_match_rows
    denom = projected_match + projected_review
    review_rate_before = review_rows / (review_rows + match_rows) if (review_rows + match_rows) else 0
    review_rate_after = projected_review / denom if denom else 0

    print(f"matched cases: {len(matched_case_ids)}")
    print(f"rows: total={total_rows} MATCH={match_rows} REVIEW={review_rows} NG={ng_rows}")
    print(f"vocab REVIEW rows: {vocab_review_rows}")
    print(f"vocab-only REVIEW rows: {vocab_only_review_rows}")
    print(f"vocab-only -> MATCH after AF: {would_match_rows}")
    print(f"REVIEW rate (MATCH+REVIEW only) before: {review_rate_before:.1%}")
    print(f"REVIEW rate (MATCH+REVIEW only) after:  {review_rate_after:.1%}")


if __name__ == "__main__":
    main()
