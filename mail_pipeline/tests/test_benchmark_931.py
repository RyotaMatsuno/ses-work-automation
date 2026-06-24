# -*- coding: utf-8 -*-
"""Task AA/AB: 931件ベンチマーク（seed=42）。"""

from __future__ import annotations

import os
import random
import re
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from analyze_final import classify_by_rule_explain, is_strong_engineer_candidate

DB = os.path.join(os.path.dirname(__file__), "..", "raw_inbox.db")
SAMPLES = {"project": 400, "skip": 250, "other": 250, "engineer": 31}

_DB_MISLABEL_ENGINEER_RE = re.compile(r"直個人|直フリ|注力★直個人|おすすめ人材")
_DEMO_RE = re.compile(r"\d+歳|男性|女性|（\d{1,2}）")
_SKIP_PROJECT_ORACLE_RE = re.compile(r"【[^】]*案件|案件一覧|元請け直|BTM案件|WT案件|急募.*案件")


def _load_sample(seed: int = 42) -> list[tuple[str, str, str, str]]:
    random.seed(seed)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows_out: list[tuple[str, str, str, str]] = []
    for cat, n in SAMPLES.items():
        rows = conn.execute(
            """
            SELECT subject, sender, body_text FROM raw_emails
            WHERE classify_result=? AND body_text IS NOT NULL AND subject IS NOT NULL
            """,
            (cat,),
        ).fetchall()
        sample = rows if len(rows) < n else random.sample(rows, n)
        for r in sample:
            rows_out.append(
                (cat, r["subject"] or "", r["sender"] or "", r["body_text"] or "")
            )
    conn.close()
    return rows_out


def _run_benchmark(seed: int = 42) -> dict:
    data = _load_sample(seed)
    project_to_engineer = 0
    project_to_engineer_oracle = 0
    skip_to_project = 0
    project_to_unknown = 0
    engineer_to_unknown = 0
    engineer_to_project = 0
    engineer_ok = 0

    for cat, subj, frm, body in data:
        pred, _meta = classify_by_rule_explain(subj, frm, body)

        if cat == "project":
            if pred == "engineer":
                project_to_engineer += 1
                if not (_DB_MISLABEL_ENGINEER_RE.search(subj) and _DEMO_RE.search(subj)):
                    project_to_engineer_oracle += 1
            if pred == "unknown":
                project_to_unknown += 1

        if cat == "skip" and pred == "project" and is_strong_engineer_candidate(subj, body[:1000]):
            skip_to_project += 1

        if cat == "engineer":
            if pred == "engineer":
                engineer_ok += 1
            if pred == "unknown":
                engineer_to_unknown += 1
            if pred == "project":
                engineer_to_project += 1

    return {
        "project_to_engineer": project_to_engineer,
        "project_to_engineer_oracle": project_to_engineer_oracle,
        "skip_to_project": skip_to_project,
        "project_to_unknown": project_to_unknown,
        "engineer_to_unknown": engineer_to_unknown,
        "engineer_to_project": engineer_to_project,
        "engineer_ok": engineer_ok,
        "engineer_total": SAMPLES["engineer"],
    }


def test_benchmark_931_targets():
    m = _run_benchmark(seed=42)
    assert m["project_to_engineer_oracle"] <= 25, (
        f"project→engineer(oracle) {m['project_to_engineer_oracle']}/400 > 25 "
        f"(raw={m['project_to_engineer']})"
    )
    assert m["project_to_engineer"] <= 32, (
        f"project→engineer(raw) {m['project_to_engineer']}/400 > 32"
    )
    assert m["skip_to_project"] <= 20, f"skip→project {m['skip_to_project']}/250 > 20"
    assert m["project_to_unknown"] <= 20, f"project→unknown {m['project_to_unknown']}/400 > 20"
    assert m["engineer_to_unknown"] <= 1, f"engineer→unknown {m['engineer_to_unknown']}/31 > 1"
    assert m["engineer_to_project"] == 0, f"engineer→project {m['engineer_to_project']}/31 > 0"
    assert m["engineer_ok"] >= 25, f"engineer {m['engineer_ok']}/{m['engineer_total']} < 25"


def test_benchmark_logs_sample_mismatches(capsys):
    data = _load_sample(42)
    shown = 0
    for cat, subj, frm, body in data:
        if cat != "project":
            continue
        pred, meta = classify_by_rule_explain(subj, frm, body)
        if pred == "engineer" and not (_DB_MISLABEL_ENGINEER_RE.search(subj) and _DEMO_RE.search(subj)):
            print(
                f"[project→engineer] 件名: {subj[:60]} | "
                f"eng_hits: {meta['eng_hits'][:4]} | proj_hits: {meta['proj_hits'][:4]} | "
                f"verdict: {pred}"
            )
            shown += 1
            if shown >= 5:
                break
    assert shown > 0
