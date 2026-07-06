import json
import sqlite3
from pathlib import Path

base = Path(__file__).resolve().parents[1]
results_path = base / "logs" / "phase0_results.jsonl"
db_path = base / "logs" / "reprocess_today.db"

if results_path.exists():
    rows = []
    for line in results_path.open(encoding="utf-8"):
        if line.strip():
            rows.append(json.loads(line))
    counts = [len(r.get("results") or []) for r in rows]
    mass = sum(1 for c in counts if c > 30)
    print("phase0_results entries", len(rows))
    print("mass30+", mass)
    if counts:
        print("avg_matches", round(sum(counts) / len(counts), 2))
        print("max_matches", max(counts))

if db_path.exists():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT business_status, match_results_json FROM processed_cases").fetchall()
    mass = 0
    counts = []
    unmatchable = 0
    for row in rows:
        data = json.loads(row["match_results_json"] or "[]")
        if data and isinstance(data[0], dict) and data[0].get("unmatchable"):
            unmatchable += 1
            counts.append(0)
            continue
        counts.append(len(data))
        if len(data) > 30:
            mass += 1
    print("reprocess db cases", len(rows), "unmatchable", unmatchable, "mass30+", mass)
    if counts:
        print("avg_matches", round(sum(counts) / len(counts), 2), "max", max(counts))
