#!/usr/bin/env python3
"""Task Q integration: measure price/skill recovery on sample project emails."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SES_WORK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SES_WORK))

from mail_pipeline.mail_pipeline import VALID_SKILLS
from mail_pipeline.price_extractor import resolve_final_price
from mail_pipeline.skill_extractor import merge_extracted_skills

DB_PATH = SES_WORK / "mail_pipeline" / "raw_inbox.db"
SAMPLE_LIMIT = 50
TARGET_NO_SKILLS = 0.35
TARGET_NO_PRICE = 0.25


def _load_samples(limit: int = SAMPLE_LIMIT) -> list[tuple[str, str]]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT subject, body_text FROM raw_emails
            WHERE classify_result = 'project'
            ORDER BY rowid DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [(r["subject"] or "", r["body_text"] or "") for r in rows]
    finally:
        conn.close()


def measure(samples: list[tuple[str, str]]) -> dict:
    if not samples:
        return {"count": 0, "no_skills_pct": 0.0, "no_price_pct": 0.0}

    no_skills = 0
    no_price = 0
    for subject, body in samples:
        req, opt = merge_extracted_skills([], [], subject, body, VALID_SKILLS)
        if not req and not opt:
            no_skills += 1
        price = resolve_final_price(None, subject, body)
        if price is None:
            no_price += 1

    n = len(samples)
    return {
        "count": n,
        "no_skills_pct": no_skills / n,
        "no_price_pct": no_price / n,
        "no_skills": no_skills,
        "no_price": no_price,
    }


def main() -> int:
    samples = _load_samples()
    if not samples:
        print("No project samples in raw_inbox.db — skipping integration metrics")
        return 0

    stats = measure(samples)
    print(f"Samples: {stats['count']}")
    print(f"No skills: {stats['no_skills']}/{stats['count']} ({stats['no_skills_pct']:.1%})")
    print(f"No price:  {stats['no_price']}/{stats['count']} ({stats['no_price_pct']:.1%})")

    ok = stats["no_skills_pct"] <= TARGET_NO_SKILLS and stats["no_price_pct"] <= TARGET_NO_PRICE
    if ok:
        print("INTEGRATION OK")
        return 0
    print(
        f"INTEGRATION WARN: targets no_skills<={TARGET_NO_SKILLS:.0%}, "
        f"no_price<={TARGET_NO_PRICE:.0%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
