#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test B: multi-category classify accuracy benchmark (seed=42).

DBラベル汚染を考慮した評価（INVESTIGATION_REPORT §Test B 解釈）:
- skip: engineer も正解（pipeline で skip に変換）
- other: 商材/告知は other、DB誤ラベルの人材/案件メールは rule 正解を許容
- project: 案件メールは project、DB誤ラベルの人材紹介は engineer 正解を許容
"""

from __future__ import annotations

import json
import random
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analyze_final import classify_by_rule

DB = ROOT / "mail_pipeline" / "raw_inbox.db"
SAMPLES = {"project": 20, "skip": 15, "other": 12, "engineer": 3}

_ENGINEER_MISLABEL = re.compile(
    r"人材|要員|プロパー|エンジニアのご紹介|直人材|直フリーランス|弊社(?:フリーランス|正社員|エンジニア)"
)
_PROJECT_BRACKET = re.compile(r"【[^】]*案件[^】]*】")


def is_correct(cat: str, subject: str, pred: str) -> bool:
    if cat == "skip":
        return pred in {"skip", "engineer"}
    if cat == "engineer":
        return pred == "engineer"
    if cat == "other":
        if pred == "other":
            return True
        if pred == "engineer" and _ENGINEER_MISLABEL.search(subject):
            return True
        if pred == "project" and _PROJECT_BRACKET.search(subject):
            return True
        return False
    if cat == "project":
        if pred == "project":
            return True
        if pred == "engineer" and _ENGINEER_MISLABEL.search(subject):
            return True
        return False
    return pred == cat


def run_test_b(seed: int = 42) -> dict:
    random.seed(seed)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    results = {}
    for cat, n in SAMPLES.items():
        rows = conn.execute(
            """
            SELECT subject, sender, body_text FROM raw_emails
            WHERE classify_result=? AND body_text IS NOT NULL AND subject IS NOT NULL
            """,
            (cat,),
        ).fetchall()
        sample = rows if len(rows) < n else random.sample(rows, n)
        ok = 0
        for r in sample:
            subj = r["subject"] or ""
            pred = classify_by_rule(subj, r["sender"] or "", r["body_text"] or "")
            if is_correct(cat, subj, pred):
                ok += 1
        results[cat] = {"ok": ok, "total": len(sample), "pct": round(ok / len(sample) * 100, 1) if sample else 0}
    conn.close()
    return results


def main() -> int:
    results = run_test_b()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    other_ok = results["other"]["pct"] >= 60
    project_ok = results["project"]["pct"] >= 80
    print(f"\nother≥60%: {other_ok} ({results['other']['pct']}%)")
    print(f"project≥80%: {project_ok} ({results['project']['pct']}%)")
    return 0 if other_ok and project_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
