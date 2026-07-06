#!/usr/bin/env python3
"""拡張前後のOOV率・マッチ候補数を比較（Phase 4）。"""
from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SES_WORK = BASE_DIR.parent
OUTPUT_MD = BASE_DIR / "oov_before_after.md"
ALIASES_PATH = BASE_DIR / "skill_aliases.json"
STRUCTURED = BASE_DIR / "logs" / "structured.jsonl"
ENGINEERS = SES_WORK / "poc_engineers.json"

JST = timezone(timedelta(hours=9))

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def _load_structured_last30() -> list[dict]:
    from tools.extract_oov_20260703 import _parse_ts, _recent_case_ids

    since = datetime.now(JST) - timedelta(days=30)
    match_results = BASE_DIR / "logs" / "match_results.jsonl"
    recent_ids = _recent_case_ids(match_results, since)
    cases: list[dict] = []
    if not STRUCTURED.exists():
        return cases
    with STRUCTURED.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if recent_ids and row.get("case_id") not in recent_ids:
                continue
            cases.append(row)
    return cases


def _collect_skill_tokens(cases: list[dict], engineers_path: Path) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    for case in cases:
        for bucket in ("required_skills", "optional_skills", "ambiguous_skills"):
            for s in case.get(bucket) or []:
                tokens.append((str(s).strip(), "案件"))
    if engineers_path.exists():
        data = json.loads(engineers_path.read_text(encoding="utf-8"))
        for eng in data:
            raw = eng.get("skills") or eng.get("スキル") or ""
            if isinstance(raw, str):
                parts = [p.strip() for p in raw.replace("/", ",").split(",") if p.strip()]
            else:
                parts = [str(p).strip() for p in raw]
            for s in parts:
                tokens.append((s, "人材"))
    return [(t, src) for t, src in tokens if t]


def _is_resolved(raw: str, normalizer, gate_mod, use_pre: bool) -> bool:
    from skill_pre_normalize import pre_normalize_skill_text

    if not gate_mod.validate_skill_for_matching(raw)[0]:
        return True  # excluded from OOV denominator
    if use_pre:
        text = gate_mod.normalize_skill_text(raw)
    else:
        import unicodedata

        text = unicodedata.normalize("NFKC", (raw or "").strip())
    if gate_mod.is_process_skill_name(text):
        return True
    if not gate_mod.is_technical_skill(text):
        return True
    if use_pre:
        return normalizer.resolve_canonical(text) is not None
    # before: legacy key without pre_normalize
    key = " ".join(text.lower().split())
    if key in normalizer.hard:
        return True
    if normalizer.soft_enabled and key in normalizer.soft:
        return True
    for canon in normalizer.skill_tiers:
        if canon.lower() == key:
            return True
    return False


def _oov_rate(tokens: list[tuple[str, str]], normalizer, gate_mod, use_pre: bool) -> tuple[float, int, int]:
    oov = 0
    denom = 0
    for raw, _ in tokens:
        if not gate_mod.validate_skill_for_matching(raw)[0]:
            continue
        text = gate_mod.normalize_skill_text(raw) if use_pre else raw
        if gate_mod.is_process_skill_name(text):
            continue
        if not gate_mod.is_technical_skill(text):
            continue
        denom += 1
        if not _is_resolved(raw, normalizer, gate_mod, use_pre):
            oov += 1
    rate = (oov / denom * 100) if denom else 0.0
    return rate, oov, denom


def _skill_gate_pass_count(cases: list[dict], normalizer, gate_mod) -> int:
    from skill_gate import (
        evaluate_matchability,
        extract_raw_required_skills,
        normalize_process_skills,
        normalize_technical_skills,
    )

    passed = 0
    for case_json in cases:
        case = {"必要スキル": case_json.get("required_skills", [])}
        extracted = extract_raw_required_skills(case, case_json)
        normalized = normalize_technical_skills(extracted, normalizer, use_p1=True)
        process = normalize_process_skills(extracted, use_p1=True)
        matchable, _, _, _ = evaluate_matchability(case_json, extracted, normalized, process)
        if matchable:
            passed += 1
    return passed


def main() -> int:
    import skill_gate
    from matcher import SkillNormalizer

    cases = _load_structured_last30()
    tokens = _collect_skill_tokens(cases, ENGINEERS)
    normalizer = SkillNormalizer(ALIASES_PATH)

    rate_before, oov_before, denom = _oov_rate(tokens, normalizer, skill_gate, use_pre=False)
    rate_after, oov_after, denom2 = _oov_rate(tokens, normalizer, skill_gate, use_pre=True)

    engineers: list[dict] = []
    if ENGINEERS.exists():
        raw = json.loads(ENGINEERS.read_text(encoding="utf-8"))
        engineers = [
            {"id": e.get("id", ""), "スキル": (e.get("skills") or "").split(", "), "単価（万円）": e.get("price")}
            for e in raw
        ]

    # before: temporarily use aliases without today's additions - use backup if exists
    backup = BASE_DIR / "skill_aliases.json.bak"
    if backup.exists():
        normalizer_before = SkillNormalizer(backup)
    else:
        normalizer_before = normalizer

    # Recompute before rate with old aliases + no pre_normalize
    rate_before2, oov_b2, _ = _oov_rate(tokens, normalizer_before, skill_gate, use_pre=False)

    cand_before = _skill_gate_pass_count(cases, normalizer_before, skill_gate)
    cand_after = _skill_gate_pass_count(cases, normalizer, skill_gate)

    lines = [
        "# OOV Before/After Report (2026-07-03)",
        "",
        "## データソース",
        f"- 案件: structured.jsonl（直近30日 case_id フィルタ） {len(cases)} 件",
        f"- 人材: poc_engineers.json {len(engineers)} 名",
        f"- スキルトークン数（技術スキル分母）: {denom}",
        "",
        "## OOV率",
        "| 指標 | Before | After | 差分 |",
        "|------|--------|-------|------|",
        f"| OOV率 | {rate_before2:.1f}% | {rate_after:.1f}% | {rate_after - rate_before2:+.1f}pt |",
        f"| OOV件数 | {oov_b2} | {oov_after} | {oov_after - oov_b2:+d} |",
        f"| 対象件数 | {denom} | {denom2} | — |",
        "",
        "## マッチ候補数（skill_gate通過案件数）",
        f"- Before: {cand_before}",
        f"- After: {cand_after}",
        f"- 増分: {cand_after - cand_before:+d}",
        "",
        "## 目標",
        "- 目標 OOV率: 25%以下（起点 41%）",
        f"- 達成: {'Yes' if rate_after <= 25.0 else 'No'} ({rate_after:.1f}%)",
        "",
        "## 変更内容",
        "- skill_pre_normalize.py: NFKC/カタカナ/記号/運用保守サフィックス正規化",
        "- skill_aliases.json: OOV上位語のエイリアス追加",
        "- matcher/skill_gate: 辞書参照前に pre_normalize 適用",
        "",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT_MD)
    print(f"OOV {rate_before2:.1f}% -> {rate_after:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
