"""Phase 6 before/after zero-match rate comparison report."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SES_WORK = BASE.parent
sys.path.insert(0, str(BASE))
sys.path.insert(1, str(SES_WORK))

from hard_filters import apply_hard_filters
from matcher import (
    SkillNormalizer,
    build_skill_index,
    filter_candidates_3layer,
    filter_engineers_by_required_skills,
)

GOLDEN = SES_WORK / "golden_test" / "golden_cases.json"
OUTPUT_DIR = SES_WORK / "research_results"

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
        "experience_years": baseline.get("experience_years"),
    }
    return notion_case, case_json


def _synthetic_engineers() -> list[dict]:
    areas = ["東京", "新宿", "渋谷", "横浜", "大阪", "名古屋", None]
    stations = ["新宿", "渋谷", "池袋", "品川", "横浜", "大阪", None]
    rates = [45, 55, 65, 75, 85, 95, None]
    skills_pool = [
        ["Java", "Spring"],
        ["Python", "Django"],
        ["AWS", "Terraform"],
        ["React", "TypeScript"],
        ["C#", ".NET"],
        ["Go", "PostgreSQL"],
        ["JavaScript", "Vue.js"],
    ]
    engineers: list[dict] = []
    idx = 0
    for area, station in zip(areas, stations):
        for rate in rates:
            for skills in skills_pool:
                idx += 1
                engineers.append(
                    {
                        "id": f"synth-{idx}",
                        "名前": f"E{idx}",
                        "提案対象フラグ": idx % 17 != 0,
                        "稼働状況": "稼働中" if idx % 11 == 0 else "待機中",
                        "単価（万円）": rate,
                        "居住地": area,
                        "最寄り駅": station,
                        "正規化スキル": skills,
                        "経験年数": 3 + (idx % 6),
                        "稼働可能日": "2026-06-01" if idx % 3 else "2026-09-01",
                    }
                )
    return engineers


def _zero_match_rate(counts: list[int]) -> float:
    if not counts:
        return 0.0
    zeros = sum(1 for count in counts if count == 0)
    return zeros / len(counts)


def main() -> int:
    if not GOLDEN.exists():
        print(f"Missing {GOLDEN}")
        return 1

    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    cases = [case for case in data.get("cases", []) if case.get("group") == "A"]
    engineers = _synthetic_engineers()
    normalizer = SkillNormalizer(BASE / "skill_aliases.json")
    skill_index = build_skill_index(engineers, normalizer)

    before_counts: list[int] = []
    after_new_counts: list[int] = []
    legacy_hard_filters = {
        "rate": True,
        "remote_location": True,
        "skill_threshold": True,
        "start_timing": True,
    }

    for case in cases:
        notion_case, case_json = _case_payload(case)
        required = case_json["required_skills"]

        skill_filtered = filter_engineers_by_required_skills(
            engineers, normalizer, skill_index, required
        )
        old_survivors, _ = apply_hard_filters(
            notion_case,
            case_json,
            skill_filtered,
            normalizer,
            legacy_hard_filters,
        )
        before_counts.append(len(old_survivors))

        new_survivors, _, _ = filter_candidates_3layer(
            engineers,
            notion_case,
            case_json,
            normalizer,
            skill_index,
            required,
        )
        after_new_counts.append(len(new_survivors))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "phase6_filter_redesign",
        "cases_evaluated": len(cases),
        "engineer_pool_size": len(engineers),
        "pipeline_before": {
            "description": "skill_50pct_filter + legacy_hard_filters(all_enabled)",
            "avg_candidates": sum(before_counts) / len(before_counts) if before_counts else 0,
            "zero_match_rate": _zero_match_rate(before_counts),
            "zero_match_cases": sum(1 for c in before_counts if c == 0),
        },
        "pipeline_after_3layer": {
            "description": "filter_candidates_3layer (hard_v6 + soft + rerank)",
            "avg_candidates": sum(after_new_counts) / len(after_new_counts) if after_new_counts else 0,
            "zero_match_rate": _zero_match_rate(after_new_counts),
            "zero_match_cases": sum(1 for c in after_new_counts if c == 0),
        },
        "target_zero_match_rate": 0.15,
        "per_case": [
            {
                "case_id": case.get("id"),
                "before_legacy": before_counts[i],
                "after_3layer": after_new_counts[i],
            }
            for i, case in enumerate(cases)
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    json_path = OUTPUT_DIR / f"phase6_zero_match_report_{stamp}.json"
    md_path = OUTPUT_DIR / f"phase6_zero_match_report_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Phase 6 Zero-Match Rate Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Cases: {report['cases_evaluated']}",
        f"- Engineer pool: {report['engineer_pool_size']}",
        "",
        "## Before (legacy pipeline)",
        f"- Zero-match rate: {report['pipeline_before']['zero_match_rate']:.1%}",
        f"- Avg candidates: {report['pipeline_before']['avg_candidates']:.1f}",
        "",
        "## After (3-layer filter)",
        f"- Zero-match rate: {report['pipeline_after_3layer']['zero_match_rate']:.1%}",
        f"- Avg candidates: {report['pipeline_after_3layer']['avg_candidates']:.1f}",
        "",
        f"Target zero-match rate: <{report['target_zero_match_rate']:.0%}",
    ]
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
