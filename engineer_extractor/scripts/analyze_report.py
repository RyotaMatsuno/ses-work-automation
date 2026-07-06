"""Analyze dry-run detailed_report.json for E2/E3 review."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUTPUT = Path(__file__).resolve().parent.parent / "output" / "detailed_report.json"


def main() -> None:
    with OUTPUT.open(encoding="utf-8") as f:
        data = json.load(f)
    records = data["records"]
    updates: list[dict] = []
    for r in records:
        for d in r.get("decisions", []):
            if d["action"] == "update":
                updates.append(
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "pattern": r["pattern"],
                        "field": d["field"],
                        "old": d["old"],
                        "new": d["new"],
                        "confidence": d["confidence"],
                        "source": d["source"],
                    }
                )

    print(f"Total update candidates: {len(updates)}")
    by_field: dict[str, list[dict]] = {}
    for u in updates:
        by_field.setdefault(u["field"], []).append(u)
    for field, items in sorted(by_field.items()):
        print(f"\n=== {field} ({len(items)}) ===")
        for u in items[:20]:
            print(
                f"  {u['name']}: {u['old']} -> {u['new']} "
                f"(conf={u['confidence']}, src={u['source']}, pat={u['pattern']})"
            )
        if len(items) > 20:
            print(f"  ... +{len(items) - 20} more")

    low = [u for u in updates if u["confidence"] < 0.7]
    print(f"\nLow confidence updates (<0.7): {len(low)}")
    for u in low:
        print(f"  {u['name']}/{u['field']}: {u['old']} -> {u['new']} conf={u['confidence']}")

    errs = [r for r in records if r.get("errors")]
    print(f"\nRecords with errors: {len(errs)}")
    for r in errs:
        print(f"  {r.get('name')}: {r['errors']}")

    # Sample 30 for manual review (diverse fields)
    print("\n=== 30-sample manual review set ===")
    sample: list[dict] = []
    per_field_limit = {"稼働可能日": 15, "スキル": 8, "経験年数": 4, "最寄り駅": 2, "単価（万円）": 1}
    for field, limit in per_field_limit.items():
        items = [u for u in updates if u["field"] == field]
        sample.extend(items[:limit])
    for i, u in enumerate(sample[:30], 1):
        print(f"{i:2}. [{u['field']}] {u['name']}: {u['old']} -> {u['new']} (conf={u['confidence']})")


if __name__ == "__main__":
    main()
