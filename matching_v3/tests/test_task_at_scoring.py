from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SES_WORK = Path(__file__).resolve().parents[2]
if str(SES_WORK) not in sys.path:
    sys.path.insert(0, str(SES_WORK))

from common.failure_collector import collect_failure
from matcher import SkillNormalizer, _calc_match_score, judge_with_meta
from scripts.discover_unknown_skills import _extract_unknown_tokens, discover


def _normalizer() -> SkillNormalizer:
    return SkillNormalizer("skill_aliases.json")


def _fresh_engineer(**overrides):
    base = {
        "単価（万円）": 60,
        "_last_edited_time": datetime.now(timezone.utc).isoformat(),
        "スキル": ["Java", "Spring", "MySQL"],
    }
    base["備考（LINEメモ）"] = ""
    base.update(overrides)
    return base


def test_calc_match_score_prefers_fresh_and_skill_hits():
    high = _calc_match_score(
        _fresh_engineer(),
        ["Java", "Spring", "MySQL"],
        [],
        [],
        80,
        60,
    )
    stale = _fresh_engineer(
        スキル=["Java"],
        _last_edited_time="2026-01-01T00:00:00+00:00",
    )
    stale["備考（LINEメモ）"] = "面談予定"
    low = _calc_match_score(
        stale,
        ["Java"],
        [],
        [],
        62,
        60,
    )
    assert high > low


def test_judge_with_meta_includes_score():
    case = {"required_skills": ["Java"], "price_max": 80, "extraction_confidence": 1.0}
    result = judge_with_meta(case, _fresh_engineer(), _normalizer())
    assert "score" in result
    assert result["score"] > 0


def test_results_sort_by_score_desc():
    rows = [{"score": 1.1}, {"score": 1.8}, {"score": 1.3}]
    rows.sort(key=lambda item: item.get("score", 0.0), reverse=True)
    assert [row["score"] for row in rows] == [1.8, 1.3, 1.1]


def test_failure_collector_respects_daily_limit(tmp_path, monkeypatch):
    import common.failure_collector as fc

    monkeypatch.setattr(fc, "_LOG_ROOT", tmp_path)
    monkeypatch.setattr(fc, "MAX_PER_DAY", 2)
    assert collect_failure("no_match", {"case_id": "1"}, "r1") is True
    assert collect_failure("no_match", {"case_id": "2"}, "r2") is True
    assert collect_failure("no_match", {"case_id": "3"}, "r3") is False


def test_extract_unknown_tokens_from_review_reason():
    reason = "語彙外必須スキル要確認: Rust, Zig"
    tokens = _extract_unknown_tokens(reason)
    assert "Rust" in tokens
    assert "Zig" in tokens


def test_discover_outputs_candidates(tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "processed.db"
    aliases_path = tmp_path / "aliases.json"
    aliases_path.write_text(
        json.dumps({"aliases": {}, "soft_aliases": {}, "canonical_skills": ["Java"], "skill_tiers": {}}),
        encoding="utf-8",
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE processed_cases (
                case_id TEXT PRIMARY KEY,
                match_results_json TEXT,
                updated_at TEXT
            )
            """
        )
        results = json.dumps(
            [
                {
                    "verdict": "REVIEW",
                    "reasons": ["語彙外必須スキル要確認: Mojo, Mojo, Mojo"],
                }
            ],
            ensure_ascii=False,
        )
        for idx in range(3):
            conn.execute(
                "INSERT INTO processed_cases(case_id, match_results_json, updated_at) VALUES (?, ?, datetime('now'))",
                (f"c{idx}", results,),
            )

    out_dir = tmp_path / "unknown"
    monkeypatch.setattr("scripts.discover_unknown_skills.OUTPUT_DIR", out_dir)
    output = discover(db_path=db_path, aliases_path=aliases_path, min_count=3)
    assert output is not None
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["candidates"][0]["skill"] == "Mojo"
