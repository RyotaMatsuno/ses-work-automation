#!/usr/bin/env python3
"""未知スキル候補の自動発見（Task AT / AW）。"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

JST = timezone(timedelta(hours=9))
SES_WORK = Path(__file__).resolve().parent.parent
MATCHING_V3 = SES_WORK / "matching_v3"
DB_PATH = MATCHING_V3 / "matching_v3_processed.db"
ALIASES_PATH = MATCHING_V3 / "skill_aliases.json"
OUTPUT_DIR = SES_WORK / "logs" / "unknown_skill_candidates"

_UNKNOWN_PATTERNS = [
    re.compile(r"語彙外必須スキル要確認:\s*(.+)"),
    re.compile(r"語彙外スキル\((\d+)件\)"),
    re.compile(r"未登録[：:]\s*(.+)"),
]


def _load_known_keys(aliases_path: Path) -> set[str]:
    data = json.loads(aliases_path.read_text(encoding="utf-8"))
    keys = set()
    for bucket in ("aliases", "soft_aliases"):
        keys.update(str(k).lower() for k in data.get(bucket, {}))
    keys.update(str(skill).lower() for skill in data.get("canonical_skills", []))
    keys.update(str(k).lower() for k in data.get("skill_tiers", {}))
    return keys


def _extract_unknown_tokens(reason: str) -> list[str]:
    tokens: list[str] = []
    for pattern in _UNKNOWN_PATTERNS:
        match = pattern.search(reason)
        if not match:
            continue
        chunk = match.group(1)
        for part in re.split(r"[,、]", chunk):
            skill = part.strip().strip("[]'\"")
            if skill and not skill.isdigit():
                tokens.append(skill)
    return tokens


def _fetch_recent_review_reasons(db_path: Path, days: int = 7) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    since = (datetime.now(JST) - timedelta(days=days)).date().isoformat()
    rows: list[dict[str, Any]] = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        for row in conn.execute(
            """
            SELECT case_id, match_results_json, updated_at
            FROM processed_cases
            WHERE date(updated_at) >= ? AND match_results_json IS NOT NULL
            """,
            (since,),
        ):
            try:
                results = json.loads(row["match_results_json"])
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(results, list):
                continue
            for item in results:
                if not isinstance(item, dict):
                    continue
                if item.get("verdict") not in ("REVIEW", "PARTIAL_MATCH"):
                    continue
                for reason in item.get("reasons") or []:
                    rows.append(
                        {
                            "case_id": row["case_id"],
                            "updated_at": row["updated_at"],
                            "reason": str(reason),
                        }
                    )
    return rows


def discover(
    *,
    db_path: Path = DB_PATH,
    aliases_path: Path = ALIASES_PATH,
    days: int = 7,
    min_count: int = 3,
) -> Path | None:
    known = _load_known_keys(aliases_path)
    recent = _fetch_recent_review_reasons(db_path, days=days)
    counter: dict[str, int] = defaultdict(int)
    contexts: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in recent:
        for token in _extract_unknown_tokens(row["reason"]):
            key = token.lower()
            if key in known:
                continue
            counter[token] += 1
            if len(contexts[token]) < 3:
                contexts[token].append(
                    {
                        "case_id": row["case_id"],
                        "reason": row["reason"],
                        "updated_at": row["updated_at"],
                    }
                )

    candidates = [
        {
            "skill": skill,
            "count": count,
            "contexts": contexts[skill],
        }
        for skill, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        if count >= min_count
    ]
    if not candidates:
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{datetime.now(JST).date().isoformat()}.json"
    out_path.write_text(json.dumps({"candidates": candidates}, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def main() -> int:
    output = discover()
    if output:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
