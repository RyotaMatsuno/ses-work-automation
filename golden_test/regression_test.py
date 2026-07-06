# -*- coding: utf-8 -*-
"""Regression test for R1-R4 extraction baseline + R5 extractor smoke tests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SES_WORK = Path(__file__).resolve().parents[1]
GOLDEN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SES_WORK))

from extractors.location_extractor import extract_location
from extractors.rate_extractor import extract_rate
from extractors.remote_extractor import extract_remote
from mail_pipeline.project_notion_save import prepare_notion_project_fields
from mail_pipeline.skill_extractor import extract_skills


def _load_cases() -> list[dict[str, Any]]:
    path = GOLDEN_DIR / "golden_cases.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path} — run build_golden_set.py first")
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("cases", [])


def _normalize_skills(skills: list[str]) -> list[str]:
    return sorted({s.strip() for s in skills if s and str(s).strip()})


def _run_legacy_regression(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    subject = case["source_text"][:120]
    body = case["source_text"]
    current = case["current_values"]
    baseline = case.get("baseline_extraction") or {}

    req, opt, price, location = prepare_notion_project_fields({}, subject, body)

    expected_req = _normalize_skills(baseline.get("required_skills") or [])
    actual_req = _normalize_skills(req)
    if expected_req and set(expected_req) != set(actual_req):
        errors.append(f"required_skills changed: {expected_req} -> {actual_req}")

    expected_price = baseline.get("rate_man", current.get("rate_man"))
    if expected_price is not None and expected_price > 0:
        if price != expected_price:
            errors.append(f"price changed: {expected_price} -> {price}")

    expected_loc = (baseline.get("location") or current.get("location") or "").strip()
    if expected_loc:
        actual_loc = (location or "").strip()
        if actual_loc and expected_loc not in actual_loc and actual_loc not in expected_loc:
            errors.append(f"location changed: {expected_loc!r} -> {actual_loc!r}")

    return errors


def _run_extractor_smoke(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    text = case["source_text"]
    try:
        extract_rate(text)
        extract_remote(text)
        extract_location(text)
    except Exception as exc:
        errors.append(f"extractor exception: {exc}")
    return errors


def _score_gold_labels(case: dict[str, Any]) -> dict[str, float] | None:
    gold = case.get("gold_labels") or {}
    if not gold.get("rate_type") and not gold.get("remote_type"):
        return None

    text = case["source_text"]
    scores: dict[str, float] = {}
    rate = extract_rate(text)
    if gold.get("rate_type"):
        scores["rate_type"] = 1.0 if rate.rate_type == gold["rate_type"] else 0.0
    if gold.get("remote_type"):
        remote = extract_remote(text)
        scores["remote_type"] = 1.0 if remote.remote_type == gold["remote_type"] else 0.0
    return scores


def test_r5_bugfix_skill_cap_70():
    rate = extract_rate("70万（スキル見合い）")
    assert rate.rate_type == "skill_dependent_with_cap"
    assert rate.rate_max_man == 70


def test_r5_bugfix_tanka_55_not_yen():
    rate = extract_rate("単価：55万")
    assert rate.rate_max_man == 55
    assert rate.rate_max_man != 550000


def test_r5_bugfix_full_remote_initial_onsite():
    remote = extract_remote("フルリモート...初日出社有")
    assert remote.remote_type == "full_remote"
    assert remote.initial_onsite is True


def test_r5_bugfix_approx_50_man():
    rate = extract_rate("50万円前後")
    assert rate.rate_type == "fixed_upper_only"
    assert rate.rate_max_man == 50


def run() -> int:
    cases = _load_cases()
    regressions: list[str] = []
    group_stats = {"A": 0, "B": 0, "C": 0}
    gold_scores: list[dict[str, float]] = []

    for case in cases:
        group = case.get("group", "?")
        group_stats[group] = group_stats.get(group, 0) + 1
        cid = case.get("case_id", "?")[:8]

        smoke_errors = _run_extractor_smoke(case)
        if smoke_errors:
            regressions.extend(f"[{group}/{cid}] {e}" for e in smoke_errors)

        if group == "B":
            legacy_errors = _run_legacy_regression(case)
            if legacy_errors:
                regressions.extend(f"[B/{cid}] {e}" for e in legacy_errors)

        if group == "A":
            scores = _score_gold_labels(case)
            if scores:
                gold_scores.append(scores)

    print("=== Regression Test Summary ===")
    print(f"Cases: {len(cases)} (A={group_stats.get('A',0)}, B={group_stats.get('B',0)}, C={group_stats.get('C',0)})")
    if gold_scores:
        fields = sorted({k for s in gold_scores for k in s})
        for field in fields:
            avg = sum(s[field] for s in gold_scores if field in s) / len(gold_scores)
            print(f"A-group {field} accuracy: {avg:.1%} ({len(gold_scores)} labeled)")
    else:
        print("A-group gold_labels: empty (manual annotation pending)")

    if regressions:
        print(f"\nFAILURES ({len(regressions)}):")
        for err in regressions[:20]:
            print(f"  - {err}")
        if len(regressions) > 20:
            print(f"  ... and {len(regressions) - 20} more")
        return 1

    print("\nPASS: no regressions detected")
    return 0


def _report_metrics() -> int:
    baseline_path = GOLDEN_DIR / "baseline_metrics.json"
    anomaly_path = SES_WORK / "research_results" / "anomaly_report.csv"
    if not baseline_path.exists():
        print(f"Missing baseline: {baseline_path}")
        return 1

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    anomaly_count = 0
    if anomaly_path.exists():
        lines = anomaly_path.read_text(encoding="utf-8").strip().splitlines()
        anomaly_count = max(0, len(lines) - 1)

    cases = _load_cases()
    gold_scores: list[dict[str, float]] = []
    for case in cases:
        if case.get("group") != "A":
            continue
        scores = _score_gold_labels(case)
        if scores:
            gold_scores.append(scores)

    print("=== R5 Backfill Metrics Report ===")
    print(f"Baseline generated: {baseline.get('generated_at')}")
    print(f"Active cases (baseline): {baseline.get('total_cases')}")
    print(f"Price empty rate (before): {baseline.get('price_empty_rate', 0):.1%}")
    print(f"Location empty rate (before): {baseline.get('location_empty_rate', 0):.1%}")
    print(f"Remote empty rate (before): {baseline.get('remote_empty_rate', 0):.1%}")
    print(f"Safety scan anomalies (pre-backfill): {anomaly_count}")
    if gold_scores:
        for field in sorted({k for s in gold_scores for k in s}):
            avg = sum(s[field] for s in gold_scores if field in s) / len(gold_scores)
            print(f"Extractor {field} accuracy (golden A): {avg:.1%}")
    print("Note: re-run scripts/safety_scan.py after backfill for post metrics")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="Print before/after metrics summary")
    args = parser.parse_args()
    if args.report:
        raise SystemExit(_report_metrics())
    raise SystemExit(run())
