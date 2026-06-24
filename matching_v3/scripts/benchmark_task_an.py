"""Task AN: matching judge フェーズの高速化ベンチマーク（LLM呼び出しなし）。"""
from __future__ import annotations

import json
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from matcher import (  # noqa: E402
    SkillNormalizer,
    build_skill_index,
    filter_engineers_by_required_skills,
    judge_with_meta,
    partition_fresh_engineers,
)
from processed_db import ProcessedDB  # noqa: E402

ALIASES_PATH = BASE / "skill_aliases.json"
FIXTURES_PATH = BASE / "tests" / "fixtures.json"
STRUCTURED_PATH = BASE / "logs" / "structured.jsonl"
ENGINEER_COUNT = 400
CASE_LIMIT = 40
STALE_RATIO = 0.15
SEED = 42
REPEAT = 2


def _load_cases() -> list[dict]:
    cases: list[dict] = []
    if STRUCTURED_PATH.exists():
        with STRUCTURED_PATH.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("required_skills"):
                    cases.append(row)
                if len(cases) >= CASE_LIMIT:
                    break
    if cases:
        return cases
    data = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    return [item["expected"] for item in data["case_examples"]]


def _synthetic_engineers(normalizer: SkillNormalizer, count: int) -> list[dict]:
    canonicals = list(normalizer.skill_tiers.keys())
    if not canonicals:
        canonicals = ["Java", "Python", "React", "AWS", "Spring", "MySQL", "TypeScript"]
    rng = random.Random(SEED)
    now = datetime.now(timezone.utc)
    engineers: list[dict] = []
    stale_count = int(count * STALE_RATIO)
    for i in range(count):
        skill_count = rng.randint(2, 6)
        skills = rng.sample(canonicals, k=min(skill_count, len(canonicals)))
        days_old = 25 if i < stale_count else rng.randint(0, 15)
        edited = (now - timedelta(days=days_old)).isoformat()
        engineers.append(
            {
                "id": f"synth-{i:04d}",
                "名前": f"Synth {i}",
                "スキル": skills,
                "単価（万円）": rng.randint(50, 85),
                "_last_edited_time": edited,
            }
        )
    return engineers


def _time_baseline(cases: list[dict], engineers: list[dict], normalizer: SkillNormalizer) -> tuple[float, int]:
    judged = 0
    start = time.perf_counter()
    for case_json in cases:
        for engineer in engineers:
            judge_with_meta(case_json, engineer, normalizer)
            judged += 1
    return time.perf_counter() - start, judged


def _time_optimized(cases: list[dict], engineers: list[dict], normalizer: SkillNormalizer) -> tuple[float, int, int]:
    fresh, _ = partition_fresh_engineers(engineers, log=None)
    index = build_skill_index(fresh, normalizer)
    judged = 0
    filtered_total = 0
    start = time.perf_counter()
    for case_json in cases:
        required = case_json.get("required_skills") or []
        candidates = filter_engineers_by_required_skills(fresh, normalizer, index, required)
        filtered_total += len(candidates)

        def _judge_one(engineer: dict) -> None:
            judge_with_meta(case_json, engineer, normalizer)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(_judge_one, engineer) for engineer in candidates]
            for future in as_completed(futures):
                future.result()
                judged += 1
    return time.perf_counter() - start, judged, filtered_total


def _benchmark_skip_pass(case_ids: list[str], last_edited: str) -> tuple[float, int]:
    db_path = BASE / "logs" / "benchmark_an_skip.db"
    if db_path.exists():
        db_path.unlink()
    db = ProcessedDB(db_path)
    for case_id in case_ids:
        db.update_status(case_id, "matched", [], case_last_edited_at=last_edited)

    start = time.perf_counter()
    skipped = sum(1 for case_id in case_ids if db.should_skip_unchanged_case(case_id, last_edited))
    elapsed = time.perf_counter() - start
    return elapsed, skipped


def main() -> None:
    normalizer = SkillNormalizer(ALIASES_PATH)
    cases = _load_cases()
    engineers = _synthetic_engineers(normalizer, ENGINEER_COUNT)

    baseline_sec = optimized_sec = 0.0
    baseline_judges = optimized_judges = 0
    filtered_total = 0
    for _ in range(REPEAT):
        sec, judged = _time_baseline(cases, engineers, normalizer)
        baseline_sec += sec
        baseline_judges = judged
        sec, judged, filtered_total = _time_optimized(cases, engineers, normalizer)
        optimized_sec += sec
        optimized_judges = judged

    baseline_sec /= REPEAT
    optimized_sec /= REPEAT
    speedup_pct = (1 - optimized_sec / baseline_sec) * 100 if baseline_sec else 0.0
    judge_reduction_pct = (1 - optimized_judges / baseline_judges) * 100 if baseline_judges else 0.0

    case_ids = [f"bench-case-{i}" for i in range(len(cases))]
    skip_sec, skipped = _benchmark_skip_pass(case_ids, "2026-06-23T10:00:00Z")

    print("=== Task AN benchmark (judge phase only) ===")
    print(f"cases: {len(cases)} engineers: {len(engineers)} (stale ratio ~{STALE_RATIO:.0%})")
    print(f"baseline judges: {baseline_judges} time: {baseline_sec:.3f}s")
    print(f"optimized judges: {optimized_judges} time: {optimized_sec:.3f}s")
    print(f"candidate pool (sum per case): {filtered_total}")
    print(f"judge call reduction: {judge_reduction_pct:.1f}%")
    print(f"time speedup: {speedup_pct:.1f}%")
    print(f"skip pass: {skipped}/{len(case_ids)} cases skipped in {skip_sec:.4f}s")
    ok = speedup_pct >= 50.0 or judge_reduction_pct >= 50.0
    print("PASS" if ok else f"WARN (time {speedup_pct:.1f}%, judge reduction {judge_reduction_pct:.1f}%)")


if __name__ == "__main__":
    main()
