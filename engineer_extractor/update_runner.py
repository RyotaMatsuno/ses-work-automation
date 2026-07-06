"""Update runner — dry-run / shadow-write / apply modes."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_SES_WORK = str(Path(__file__).resolve().parent.parent)
if _SES_WORK not in sys.path:
    sys.path.insert(0, _SES_WORK)

from dotenv import load_dotenv

from engineer_extractor.engineer_text_parser import parse_engineer_text
from engineer_extractor.field_extractors.skills_extractor import extract_skills
from engineer_extractor.field_extractors.rate_extractor_eng import extract_rate
from engineer_extractor.field_extractors.station_extractor import extract_station
from engineer_extractor.field_extractors.experience_extractor import extract_experience
from engineer_extractor.field_extractors.availability_extractor import extract_availability
from engineer_extractor.field_extractors.demographics_extractor import extract_demographics
from engineer_extractor.merge_policy import decide_merge, MergeDecision

import requests

_ENV_PATH = Path(__file__).parent.parent / "config" / ".env"
load_dotenv(_ENV_PATH)

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
NOTION_VERSION = "2022-06-28"
_RATE_LIMIT_SLEEP = 0.35
_OUTPUT_DIR = Path(__file__).parent / "output"


def _notion_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _fetch_all_engineers() -> list[dict]:
    url = f"https://api.notion.com/v1/databases/{ENGINEER_DB_ID}/query"
    headers = _notion_headers()
    records = []
    payload: dict = {"page_size": 100}
    while True:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
        time.sleep(_RATE_LIMIT_SLEEP)
    return records


def _get_text_prop(props: dict, *keys: str) -> str:
    for key in keys:
        prop = props.get(key)
        if not prop:
            continue
        if isinstance(prop.get("rich_text"), list):
            return "".join(b["plain_text"] for b in prop["rich_text"])
        if isinstance(prop.get("title"), list):
            return "".join(b["plain_text"] for b in prop["title"])
    return ""


def _get_number_prop(props: dict, key: str) -> float | None:
    prop = props.get(key)
    if prop and prop.get("number") is not None:
        return prop["number"]
    return None


def _get_multi_select_prop(props: dict, key: str) -> list[str]:
    prop = props.get(key)
    if prop and isinstance(prop.get("multi_select"), list):
        return [o["name"] for o in prop["multi_select"]]
    return []


def _get_select_prop(props: dict, key: str) -> str | None:
    prop = props.get(key)
    if prop and prop.get("select") and prop["select"].get("name"):
        return prop["select"]["name"]
    return None


def _get_date_prop(props: dict, key: str) -> str | None:
    prop = props.get(key)
    if prop and prop.get("date") and prop["date"].get("start"):
        return prop["date"]["start"]
    return None


def _build_patch_payload(decisions: list[MergeDecision]) -> dict:
    props: dict = {}
    for d in decisions:
        if d.action != "update":
            continue
        field = d.field
        val = d.new_value

        if field == "スキル":
            props[field] = {"multi_select": [{"name": s} for s in (val or [])]}
        elif field == "単価（万円）":
            props[field] = {"number": val}
        elif field == "最寄り駅":
            props[field] = {"rich_text": [{"text": {"content": str(val)}}]}
        elif field == "経験年数":
            props[field] = {"number": val}
        elif field == "稼働可能日":
            props[field] = {"date": {"start": str(val)}}
        elif field == "居住地":
            props[field] = {"select": {"name": str(val)}}

    return props


def _patch_notion_page(page_id: str, properties: dict) -> None:
    url = f"https://api.notion.com/v1/pages/{page_id}"
    resp = requests.patch(url, headers=_notion_headers(), json={"properties": properties}, timeout=30)
    resp.raise_for_status()
    time.sleep(_RATE_LIMIT_SLEEP)


def _process_record(record: dict) -> dict:
    page_id = record["id"]
    props = record.get("properties", {})

    name = _get_text_prop(props, "名前", "氏名", "エンジニア名")
    raw_text1 = _get_text_prop(props, "人員情報原文", "原文")
    raw_text2 = _get_text_prop(props, "備考（LINEメモ）", "備考LINEメモ", "備考", "LINEメモ")
    full_text = "\n".join(filter(None, [raw_text1, raw_text2]))

    parsed = parse_engineer_text(full_text)

    skills_r = extract_skills(parsed)
    rate_r = extract_rate(parsed)
    station_r = extract_station(parsed)
    exp_r = extract_experience(parsed)
    avail_r = extract_availability(parsed)
    demo_r = extract_demographics(parsed)

    extracted: dict = {}
    confidences: dict = {}
    sources: dict = {}

    if skills_r.skills:
        extracted["スキル"] = skills_r.skills
        confidences["スキル"] = skills_r.confidence
        sources["スキル"] = skills_r.source

    if rate_r.rate is not None and not rate_r.skill_dependent:
        extracted["単価（万円）"] = rate_r.rate
        confidences["単価（万円）"] = rate_r.confidence
        sources["単価（万円）"] = rate_r.source

    if station_r.station:
        extracted["最寄り駅"] = station_r.station
        confidences["最寄り駅"] = station_r.confidence
        sources["最寄り駅"] = station_r.source

    if exp_r.years is not None:
        extracted["経験年数"] = exp_r.years
        confidences["経験年数"] = exp_r.confidence
        sources["経験年数"] = exp_r.source

    if avail_r.start_date:
        extracted["稼働可能日"] = avail_r.start_date
        confidences["稼働可能日"] = avail_r.confidence
        sources["稼働可能日"] = avail_r.source

    existing: dict = {
        "スキル": _get_multi_select_prop(props, "スキル"),
        "単価（万円）": _get_number_prop(props, "単価（万円）"),
        "最寄り駅": _get_text_prop(props, "最寄り駅"),
        "経験年数": _get_number_prop(props, "経験年数"),
        "稼働可能日": _get_date_prop(props, "稼働可能日"),
        "居住地": _get_select_prop(props, "居住地"),
    }

    decisions = decide_merge(existing, extracted, confidences, sources)

    return {
        "id": page_id,
        "name": name,
        "pattern": parsed.pattern_type,
        "extracted": {
            "skills": {"value": skills_r.skills, "confidence": skills_r.confidence, "source": skills_r.source},
            "rate": {"value": rate_r.rate, "confidence": rate_r.confidence, "source": rate_r.source},
            "station": {"value": station_r.station, "confidence": station_r.confidence, "source": station_r.source},
            "experience": {"value": exp_r.years, "confidence": exp_r.confidence, "source": exp_r.source},
            "availability": {"value": avail_r.start_date, "confidence": avail_r.confidence, "source": avail_r.source},
        },
        "decisions": [
            {
                "field": d.field, "action": d.action,
                "old": d.old_value, "new": d.new_value,
                "confidence": d.confidence, "source": d.source,
            }
            for d in decisions
        ],
        "errors": [],
    }


def _print_summary(results: list[dict]) -> None:
    total = len(results)
    pattern_counts: dict[str, int] = {}
    field_stats: dict[str, dict[str, int]] = {}

    for r in results:
        p = r["pattern"]
        pattern_counts[p] = pattern_counts.get(p, 0) + 1
        for d in r.get("decisions", []):
            f = d["field"]
            if f not in field_stats:
                field_stats[f] = {"update": 0, "skip_existing": 0, "skip_no_value": 0}
            field_stats[f][d["action"]] = field_stats[f].get(d["action"], 0) + 1

    print(f"\n{'='*60}")
    print(f"  Engineer DB Update Report — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Total records: {total}")
    print(f"{'='*60}")
    print("  Pattern distribution:")
    for p, c in sorted(pattern_counts.items()):
        print(f"    {p}: {c}")
    print("\n  Field update candidates:")
    print(f"  {'Field':<20} {'Update':>8} {'Skip(existing)':>15} {'Skip(no val)':>13}")
    print(f"  {'-'*58}")
    for field, stats in sorted(field_stats.items()):
        print(f"  {field:<20} {stats.get('update', 0):>8} {stats.get('skip_existing', 0):>15} {stats.get('skip_no_value', 0):>13}")
    print(f"{'='*60}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Engineer DB update runner")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Report only (default)")
    parser.add_argument("--shadow-write", action="store_true", help="Write shadow_report.json only")
    parser.add_argument("--apply", action="store_true", help="Apply updates to Notion")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of records to process")
    args = parser.parse_args()

    if args.apply:
        args.dry_run = False
    if args.shadow_write:
        args.dry_run = False

    _OUTPUT_DIR.mkdir(exist_ok=True)

    print("Fetching engineer records from Notion...")
    records = _fetch_all_engineers()
    if args.limit:
        records = records[: args.limit]
    print(f"Fetched {len(records)} records.")

    results = []
    for rec in records:
        try:
            result = _process_record(rec)
        except Exception as e:
            result = {"id": rec.get("id", "?"), "name": "?", "pattern": "error", "errors": [str(e)], "decisions": []}
        results.append(result)

    _print_summary(results)

    report_path = _OUTPUT_DIR / "detailed_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "records": results}, f, ensure_ascii=False, indent=2)
    print(f"Detailed report written to: {report_path}")

    if args.apply:
        # save snapshot
        snapshot_path = _OUTPUT_DIR / "pre_update_snapshot.json"
        with snapshot_path.open("w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "records": results}, f, ensure_ascii=False, indent=2)
        print(f"Snapshot saved: {snapshot_path}")

        update_log = []
        for r in results:
            updates = [d for d in r.get("decisions", []) if d["action"] == "update"]
            if not updates:
                continue
            merge_decisions = [
                MergeDecision(
                    field=d["field"], action=d["action"],
                    old_value=d["old"], new_value=d["new"],
                    confidence=d["confidence"], source=d["source"],
                )
                for d in r["decisions"]
            ]
            patch = _build_patch_payload(merge_decisions)
            if not patch:
                continue
            try:
                _patch_notion_page(r["id"], patch)
                update_log.append({"id": r["id"], "name": r["name"], "updates": patch})
                print(f"  Updated: {r['name']} ({r['id'][:8]}...)")
            except Exception as e:
                print(f"  ERROR updating {r['name']}: {e}", file=sys.stderr)

        log_path = _OUTPUT_DIR / "update_log.json"
        with log_path.open("w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "updates": update_log}, f, ensure_ascii=False, indent=2)
        print(f"Update log: {log_path}")

    elif args.shadow_write:
        shadow_path = _OUTPUT_DIR / "shadow_report.json"
        shadow_data = [
            {"id": r["id"], "name": r["name"], "decisions": [d for d in r["decisions"] if d["action"] in ("update", "skip_existing")]}
            for r in results
        ]
        with shadow_path.open("w", encoding="utf-8") as f:
            json.dump(shadow_data, f, ensure_ascii=False, indent=2)
        print(f"Shadow report: {shadow_path}")


if __name__ == "__main__":
    main()
