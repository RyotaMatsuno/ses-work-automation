"""パイプライン各段の件数計測スクリプト。

入力: matching_v3/logs/structured.jsonl + エンジニアDB (Notion)
出力: 各段の通過/落下件数レポート

使い方:
    cd ses_work/matching_v3
    python diagnostics/pipeline_measure.py [--structured PATH] [--no-notion]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent  # matching_v3/
SES_WORK = BASE_DIR.parent

for _p in (str(BASE_DIR), str(SES_WORK)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

DEFAULT_STRUCTURED = BASE_DIR / "logs" / "structured.jsonl"


def _load_structured(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    if not path.exists():
        print(f"[ERROR] structured.jsonl が見つかりません: {path}", file=sys.stderr)
        return cases
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    cases.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    print(f"[WARN] JSON解析失敗: {exc}", file=sys.stderr)
    return cases


def _try_load_engineers() -> list[dict[str, Any]]:
    try:
        from notion_client import NotionClient

        client = NotionClient()
        engineers = client.get_active_engineers()
        print(f"[INFO] エンジニアDB: {len(engineers)}名ロード")
        return engineers
    except Exception as exc:
        print(f"[WARN] エンジニアDB取得失敗（Stage 2-5 はスキップ）: {exc}")
        return []


def _top3(counter: Counter) -> list[tuple[str, int]]:
    return counter.most_common(3)


def _measure_hard_filters(
    cases: list[dict[str, Any]],
    engineers: list[dict[str, Any]],
) -> tuple[int, int, Counter, list[dict[str, Any]]]:
    from matcher import apply_hard_filter_v6

    total_in = 0
    total_out = 0
    drop_counter: Counter = Counter()
    cases_with_survivors: list[dict[str, Any]] = []

    for case_json in cases:
        case: dict[str, Any] = {
            "id": case_json.get("case_id", ""),
            "必要スキル": case_json.get("required_skills", []),
        }
        survivors, breakdowns, stats = apply_hard_filter_v6(engineers, case_json)
        total_in += stats.total_in
        total_out += len(survivors)
        drop_counter["proposal_flag"] += stats.dropped_proposal_flag
        drop_counter["active_working"] += stats.dropped_active_working
        drop_counter["late_start"] += stats.dropped_late_start
        if survivors:
            case_json = dict(case_json)
            case_json["_hard_survivors"] = survivors
            case_json["_hard_breakdowns"] = breakdowns
            cases_with_survivors.append(case_json)

    return total_in, total_out, drop_counter, cases_with_survivors


def _measure_skill_gate(
    cases: list[dict[str, Any]],
    normalizer: Any,
    *,
    use_p1: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter]:
    from skill_gate import (
        evaluate_matchability,
        extract_raw_required_skills,
        normalize_process_skills,
        normalize_technical_skills,
    )

    passed: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    drop_reasons: Counter = Counter()

    for case_json in cases:
        case = {"必要スキル": case_json.get("required_skills", [])}
        extracted = extract_raw_required_skills(case, case_json)
        normalized = normalize_technical_skills(extracted, normalizer, use_p1=use_p1)
        process = normalize_process_skills(extracted, use_p1=use_p1)
        matchable, _, _, ng_reason = evaluate_matchability(
            case_json,
            extracted,
            normalized,
            process,
        )
        if matchable:
            enriched = dict(case_json)
            enriched["_extracted"] = extracted
            enriched["_normalized"] = normalized
            enriched["_process"] = process
            passed.append(enriched)
        else:
            drop_reasons[ng_reason or "UNKNOWN"] += 1
            dropped.append(case_json)

    return passed, dropped, drop_reasons


def _print_p1_report(cases: list[dict[str, Any]], normalizer: Any) -> None:
    with_p1_passed, with_p1_dropped, with_p1_reasons = _measure_skill_gate(cases, normalizer, use_p1=True)
    without_p1_passed, without_p1_dropped, without_p1_reasons = _measure_skill_gate(cases, normalizer, use_p1=False)

    print("\n【P1正規化 効果測定】")
    print(f"  skill_gate通過 (P1 ON) : {len(with_p1_passed)} 件")
    print(f"  skill_gate通過 (P1 OFF): {len(without_p1_passed)} 件")
    print(
        "  ALL_REQUIRED_SKILLS_OOV (P1 ON) : "
        f"{with_p1_reasons.get('ALL_REQUIRED_SKILLS_OOV', 0)} 件"
    )
    print(
        "  ALL_REQUIRED_SKILLS_OOV (P1 OFF): "
        f"{without_p1_reasons.get('ALL_REQUIRED_SKILLS_OOV', 0)} 件"
    )
    print(f"  OOV削減: {without_p1_reasons.get('ALL_REQUIRED_SKILLS_OOV', 0) - with_p1_reasons.get('ALL_REQUIRED_SKILLS_OOV', 0)} 件")


def _measure_score_threshold(
    cases: list[dict[str, Any]],
    normalizer: Any,
    skill_index: dict[str, set[str]],
) -> tuple[int, int, list[dict[str, Any]]]:
    from config import SCORE_WEIGHTS
    from matcher import filter_candidates_3layer, score_candidate_soft

    threshold_pass = 0
    final_matches = 0
    matched_cases: list[dict[str, Any]] = []

    for case_json in cases:
        survivors = case_json.get("_hard_survivors", [])
        if not survivors:
            continue
        case: dict[str, Any] = {"id": case_json.get("case_id", "")}
        required_skills = case_json.get("_normalized") or case_json.get("required_skills", [])
        passed, _, _ = filter_candidates_3layer(
            survivors,
            case,
            case_json,
            normalizer,
            skill_index,
            required_skills,
        )
        for engineer in passed:
            breakdown = score_candidate_soft(
                engineer,
                case_json,
                normalizer,
                skill_index,
                required_skills,
                score_weights=SCORE_WEIGHTS,
            )
            if float(breakdown["scores"]["total"]) > 0:
                threshold_pass += 1
        final_matches += len(passed)
        if passed:
            enriched = dict(case_json)
            enriched["_final_candidates"] = passed
            matched_cases.append(enriched)

    return threshold_pass, final_matches, matched_cases


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="パイプライン各段の件数計測")
    parser.add_argument("--structured", default=str(DEFAULT_STRUCTURED), help="structured.jsonl のパス")
    parser.add_argument("--no-notion", action="store_true", help="Notion取得をスキップ（Stage 2-5 省略）")
    parser.add_argument("--p1-report", action="store_true", help="P1正規化のON/OFF差分を表示")
    args = parser.parse_args(argv)

    cases = _load_structured(Path(args.structured))
    if not cases:
        print("[ERROR] 入力案件が0件。終了します。")
        return

    from matcher import SkillNormalizer, build_skill_index, prepare_engineer_skills

    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")

    if args.p1_report:
        _print_p1_report(cases, normalizer)
        if args.no_notion:
            return

    sep = "=" * 60
    print(f"\n{sep}")
    print("  パイプライン計測レポート")
    print(f"{sep}")
    print(f"\n【Stage 1】入力案件数 : {len(cases)} 件")

    if args.no_notion:
        print("\n[INFO] --no-notion 指定のため Stage 2-5 をスキップ")
        print(f"\n{sep}\n")
        return

    engineers_raw = _try_load_engineers()
    if not engineers_raw:
        print(f"\n{sep}\n")
        return

    engineers = [prepare_engineer_skills(e, normalizer) for e in engineers_raw]
    skill_index = build_skill_index(engineers, normalizer)

    total_in, total_out, hf_drops, hf_cases = _measure_hard_filters(cases, engineers)
    print(f"\n【Stage 2】hard_filters通過 : {total_out} / {total_in} エンジニア-案件ペア")
    print(f"  有生存候補の案件: {len(hf_cases)} / {len(cases)} 件")
    if any(hf_drops.values()):
        print("  落下理由 TOP3:")
        for reason, cnt in _top3(hf_drops):
            print(f"    {reason}: {cnt} ペア")

    sg_passed, sg_dropped, sg_drop_reasons = _measure_skill_gate(cases, normalizer)
    print(f"\n【Stage 3】skill_gate通過 : {len(sg_passed)} 件  (落下: {len(sg_dropped)} 件)")
    if sg_drop_reasons:
        print("  落下理由 TOP3:")
        for reason, cnt in _top3(sg_drop_reasons):
            print(f"    {reason}: {cnt} 件")

    sg_by_id = {c.get("case_id"): c for c in sg_passed}
    merged_cases: list[dict[str, Any]] = []
    for case_json in hf_cases:
        case_id = case_json.get("case_id")
        sg_case = sg_by_id.get(case_id)
        if not sg_case:
            continue
        merged = dict(case_json)
        merged["_normalized"] = sg_case.get("_normalized", [])
        merged_cases.append(merged)

    threshold_pass, final_matches, _ = _measure_score_threshold(merged_cases, normalizer, skill_index)
    print(f"\n【Stage 4】スコア閾値通過 : {threshold_pass} ペア")
    print(f"\n【Stage 5】最終マッチ数    : {final_matches} ペア")
    if args.p1_report:
        _print_p1_report(cases, normalizer)

    print(f"\n{sep}\n")


if __name__ == "__main__":
    main()
