from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

JST = timezone(timedelta(hours=9))
_BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = _BASE_DIR / "logs" / "unknown_skill_candidates"
_DEFAULT_DB_PATH = _BASE_DIR / "matching_v3_processed.db"
_DEFAULT_ALIASES_PATH = _BASE_DIR / "skill_aliases.json"

_UNKNOWN_SKILL_RE = re.compile(r"語彙外必須スキル要確認[:：]\s*(.+)")


def _extract_unknown_tokens(reason: str) -> list[str]:
    """REVIEW理由文字列から語彙外スキル名を抽出する。"""
    m = _UNKNOWN_SKILL_RE.search(reason)
    if not m:
        return []
    return [t.strip() for t in m.group(1).split(",") if t.strip()]


def _load_known_skills(aliases_path: Path) -> set[str]:
    """aliases.jsonから既知スキル名の正規化セットを構築する。"""
    with aliases_path.open(encoding="utf-8") as f:
        data = json.load(f)
    known: set[str] = set()
    for skill in data.get("canonical_skills", []):
        known.add(str(skill).lower().strip())
    for key, val in data.get("aliases", {}).items():
        known.add(key.lower().strip())
        known.add(str(val).lower().strip())
    for key, val in data.get("soft_aliases", {}).items():
        known.add(key.lower().strip())
        known.add(str(val).lower().strip())
    for skill in data.get("skill_tiers", {}).keys():
        known.add(str(skill).lower().strip())
    return known


def _query_recent_review_rows(conn: sqlite3.Connection, days: int = 7) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT case_id, match_results_json, updated_at
        FROM processed_cases
        WHERE updated_at >= datetime('now', ?, '+9 hours')
          AND match_results_json IS NOT NULL
        """,
        (f"-{days} days",),
    ).fetchall()
    return [dict(row) for row in rows]


def discover(
    db_path: Path | str | None = None,
    aliases_path: Path | str | None = None,
    min_count: int = 3,
    days: int = 7,
) -> Path | None:
    """語彙外スキル候補を集計してJSONファイルに出力する。"""
    db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
    aliases_path = Path(aliases_path) if aliases_path else _DEFAULT_ALIASES_PATH

    if not db_path.exists():
        return None

    known_skills = _load_known_skills(aliases_path) if aliases_path.exists() else set()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = _query_recent_review_rows(conn, days=days)
    conn.close()

    skill_count: dict[str, int] = defaultdict(int)
    skill_contexts: dict[str, list[str]] = defaultdict(list)

    for row in rows:
        try:
            results = json.loads(row["match_results_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(results, list):
            continue

        case_skills: set[str] = set()
        case_contexts: dict[str, str] = {}
        for result in results:
            if not isinstance(result, dict):
                continue
            for reason in result.get("reasons", []):
                tokens = _extract_unknown_tokens(str(reason))
                for token in tokens:
                    norm = token.lower().strip()
                    if norm and norm not in known_skills:
                        case_skills.add(token)
                        if token not in case_contexts:
                            case_contexts[token] = str(reason)

        for skill in case_skills:
            skill_count[skill] += 1
            if len(skill_contexts[skill]) < 3:
                skill_contexts[skill].append(case_contexts.get(skill, ""))

    candidates = [
        {"skill": skill, "count": count, "contexts": skill_contexts[skill]}
        for skill, count in skill_count.items()
        if count >= min_count
    ]
    candidates.sort(key=lambda c: c["count"], reverse=True)

    if not candidates:
        return None

    today = datetime.now(JST).date().isoformat()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{today}.json"
    out_path.write_text(
        json.dumps({"generated_at": today, "candidates": candidates}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
