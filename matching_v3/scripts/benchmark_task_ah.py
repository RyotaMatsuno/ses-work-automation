"""Task AH: replay judge() on 6/23 matched 98 cases with live engineer data."""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from matcher import SkillNormalizer, judge
from notion_client import NotionClient


def _load_structured(case_ids: set[str]) -> dict[str, dict]:
    cases: dict[str, dict] = {}
    path = BASE / "logs" / "structured.jsonl"
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            case_id = row["case_id"]
            if case_id in case_ids:
                cases[case_id] = row
    return cases


def main() -> None:
    conn = sqlite3.connect(BASE / "matching_v3_processed.db")
    case_ids = {
        row[0]
        for row in conn.execute(
            "SELECT case_id FROM processed_cases WHERE date(updated_at)='2026-06-23' AND business_status='matched'"
        )
    }
    conn.close()

    structured = _load_structured(case_ids)
    missing_cases = case_ids - set(structured)
    print(f"matched cases: {len(case_ids)} structured loaded: {len(structured)} missing: {len(missing_cases)}")

    engineers = NotionClient().get_proposal_target_engineers()
    normalizer = SkillNormalizer(BASE / "skill_aliases.json")

    verdicts = Counter()
    for case_id in sorted(case_ids):
        case_json = structured.get(case_id)
        if not case_json:
            continue
        for engineer in engineers:
            verdict, _ = judge(case_json, engineer, normalizer)
            verdicts[verdict] += 1

    match_count = verdicts["MATCH"]
    review_count = verdicts["REVIEW"]
    ng_count = verdicts["NG"]
    total = match_count + review_count + ng_count
    match_review_total = match_count + review_count
    match_rate_all = match_count / total if total else 0
    match_rate_non_ng = match_count / match_review_total if match_review_total else 0

    cases_with_match = 0
    for case_id in case_ids:
        case_json = structured.get(case_id)
        if not case_json:
            continue
        if any(
            judge(case_json, engineer, normalizer)[0] == "MATCH"
            for engineer in engineers
        ):
            cases_with_match += 1
    case_match_rate = cases_with_match / len(case_ids) if case_ids else 0

    print(f"replay rows: {total}")
    print(f"MATCH={match_count} REVIEW={review_count} NG={ng_count}")
    print(f"MATCH rate (all rows): {match_rate_all:.1%}")
    print(f"MATCH rate (MATCH+REVIEW rows): {match_rate_non_ng:.1%}")
    print(f"case MATCH rate (>=1 MATCH per case): {case_match_rate:.1%} ({cases_with_match}/{len(case_ids)})")
    print("PASS" if case_match_rate >= 0.20 else "FAIL (<20% case MATCH rate)")


if __name__ == "__main__":
    main()
