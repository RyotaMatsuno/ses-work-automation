from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any

from composer import attach_drafts
from fetcher import fetch_engineers, fetch_projects
from matcher import match_projects
from skill_autofill import autofill_skills, load_anthropic_api_key


OUTPUT_PATH = "result_pipeline.json"


def clean_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": candidate.get("name", ""),
        "price": candidate.get("price"),
        "gross_profit": candidate.get("gross_profit"),
        "required_match": candidate.get("required_match", {}),
        "optional_match": candidate.get("optional_match", {}),
        "draft_mail": candidate.get("draft_mail", ""),
    }


def clean_project(project: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": project.get("name", ""),
        "price": project.get("price"),
        "required_skills": project.get("required_skills", []),
        "optional_skills": project.get("optional_skills", []),
        "location": project.get("location", ""),
        "period": project.get("period", ""),
        "detail": project.get("detail", ""),
    }


def build_result(items: list[dict[str, Any]], total_projects: int) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_projects": total_projects,
        "matched_projects": len(items),
        "items": [
            {
                "project": clean_project(item["project"]),
                "candidates": [
                    clean_candidate(candidate) for candidate in item["candidates"]
                ],
            }
            for item in items
        ],
    }


def run_pipeline(dry_run: bool = True) -> dict[str, Any]:
    api_key = load_anthropic_api_key()
    projects = fetch_projects()
    projects = autofill_skills(projects, api_key)
    engineers = fetch_engineers()
    matched_items = match_projects(projects, engineers)
    drafted_items = attach_drafts(matched_items)
    result = build_result(drafted_items, len(projects))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    if not dry_run:
        print("--run 指定ですが、Phase1ではメール送信せず出力のみ実行します。")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase1営業パイプライン")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="出力のみ実行します")
    mode.add_argument("--run", action="store_true", help="将来の送信モードです")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = not args.run
    result = run_pipeline(dry_run=dry_run)
    print(f"total_projects: {result['total_projects']}")
    print(f"matched_projects: {result['matched_projects']}")
    print(f"output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
