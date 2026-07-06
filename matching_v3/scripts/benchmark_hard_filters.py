"""Benchmark hard filter drop-off on golden cases + synthetic engineer pool."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SES_WORK = BASE.parent
sys.path.insert(0, str(BASE))
sys.path.insert(1, str(SES_WORK))

from config import HARD_FILTERS
from hard_filters import apply_hard_filters
from matcher import SkillNormalizer, build_skill_index, filter_engineers_by_required_skills

GOLDEN = SES_WORK / "golden_test" / "golden_cases.json"

sys.path.insert(0, str(SES_WORK))
from extractors.location_extractor import extract_location
from extractors.rate_extractor import extract_rate
from extractors.remote_extractor import extract_remote


def _case_payload(case: dict) -> tuple[dict, dict]:
    text = case["source_text"]
    current = case.get("current_values") or {}
    baseline = case.get("baseline_extraction") or {}
    rate = extract_rate(text)
    remote = extract_remote(text)
    location = extract_location(text)

    rate_man = rate.rate_max_man if rate.rate_max_man is not None else current.get("rate_man")
    notion_case = {
        "単価（万円）": rate_man,
        "rate_type": rate.rate_type,
        "remote_type": remote.remote_type or current.get("remote_type"),
        "勤務地": location.location or current.get("location"),
    }
    case_json = {
        "price_max": rate_man,
        "rate_type": rate.rate_type,
        "remote_type": remote.remote_type,
        "work_location": location.location or current.get("location"),
        "required_skills": baseline.get("required_skills") or current.get("required_skills") or ["Java"],
        "start_date": baseline.get("start_date"),
    }
    return notion_case, case_json


def _synthetic_engineers() -> list[dict]:
    areas = ["東京", "大阪", "名古屋", "横浜", None]
    rates = [45, 55, 65, 75, 85, 95, None]
    skills_pool = [
        ["Java", "Spring"],
        ["Python", "Django"],
        ["AWS", "Terraform"],
        ["React", "TypeScript"],
        ["C#", ".NET"],
        ["Go", "PostgreSQL"],
    ]
    engineers: list[dict] = []
    idx = 0
    for area in areas:
        for rate in rates:
            for skills in skills_pool:
                idx += 1
                engineers.append(
                    {
                        "id": f"synth-{idx}",
                        "名前": f"E{idx}",
                        "単価（万円）": rate,
                        "居住地": area,
                        "正規化スキル": skills,
                        "稼働可能日": "2026-06-01" if idx % 3 else "2026-09-01",
                    }
                )
    return engineers


def main() -> int:
    if not GOLDEN.exists():
        print(f"Missing {GOLDEN}")
        return 1

    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    engineers = _synthetic_engineers()
    normalizer = SkillNormalizer(BASE / "skill_aliases.json")
    skill_index = build_skill_index(engineers, normalizer)

    before_counts: list[int] = []
    after_counts: list[int] = []
    totals = {
        "dropped_rate": 0,
        "dropped_remote_location": 0,
        "dropped_skill_threshold": 0,
        "dropped_start_timing": 0,
    }

    for case in cases:
        if case.get("group") != "A":
            continue
        notion_case, case_json = _case_payload(case)
        required = case_json["required_skills"]
        candidates = filter_engineers_by_required_skills(engineers, normalizer, skill_index, required)
        before_counts.append(len(candidates))
        survivors, stats = apply_hard_filters(notion_case, case_json, candidates, normalizer, HARD_FILTERS)
        after_counts.append(len(survivors))
        for key in totals:
            totals[key] += getattr(stats, key)

    avg_before = sum(before_counts) / len(before_counts) if before_counts else 0
    avg_after = sum(after_counts) / len(after_counts) if after_counts else 0
    reduction = 1 - (avg_after / avg_before) if avg_before else 0
    print("=== Hard Filter Benchmark ===")
    print(f"Cases evaluated: {len(before_counts)}")
    print(f"Avg candidates before hard filter: {avg_before:.1f}")
    print(f"Avg candidates after hard filter: {avg_after:.1f}")
    print(f"Reduction rate: {reduction:.1%}")
    print(f"Drop-off totals: {totals}")
    dropped_any = sum(totals.values()) > 0
    ok = dropped_any and avg_after <= avg_before and (5 <= avg_after <= 15 or reduction >= 0.3)
    print(f"PASS: {ok} (target 5-15 avg or >=30% reduction)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
