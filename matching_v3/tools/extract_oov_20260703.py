#!/usr/bin/env python3
"""直近30日のOOVスキル語をログ/中間出力から抽出する（Phase 1）。"""
from __future__ import annotations

import ast
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).resolve().parents[1]
SES_WORK = BASE_DIR.parent
OUTPUT_CSV = BASE_DIR / "oov_report.csv"
TASKS_MD = BASE_DIR / "TASKS.md"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from matcher import SkillNormalizer  # noqa: E402
from skill_gate import (  # noqa: E402
    is_process_skill_name,
    is_technical_skill,
    normalize_skill_text,
    validate_skill_for_matching,
)

UNKNOWN_REASON_RE = re.compile(r"語彙外必須スキル要確認:\s*(.+)")
UNKNOWN_EVIDENCE_RE = re.compile(r"unknown skills with engineer DB evidence:\s*(\[.+\])")
UNMATCHABLE_RE = re.compile(
    r"UNMATCHABLE: case=([0-9a-f\-]+) status=UNMATCHABLE_SKILL_OOV"
)
# マッチングログに混入するメール定型文・制約条件（OOVレポートから除外）
_OOV_REPORT_NOISE_RES = (
    re.compile(r"(尚可|ご提案|ご回答|お願い|項番|満たし|見送り|記載|教示|連絡)"),
    re.compile(r"(万円|外国籍|年齢|出社|出勤|オフィス|ハイブリッド|リモート|フルリモ|出張)"),
    re.compile(r"^[@＠○●△×〇]"),
    re.compile(r"^(に|の|と|および|内容|可能|スキル)\b"),
    re.compile(r"スキル\s*[:：]"),
    re.compile(r"^[(\[【]"),
    re.compile(r"[)）]$"),
    re.compile(r"\d+歳"),
    re.compile(r"^です[。.]?$"),
    re.compile(r"^となる|^に応じて|^への適合"),
    re.compile(r"^7月"),
    re.compile(r"募集中|提案不可|適合状況"),
)


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _split_skills(chunk: str) -> list[str]:
    parts = re.split(r"[,、]", chunk)
    return [p.strip().strip("[]'\"") for p in parts if p.strip()]


def _is_oov_token(raw: str, normalizer: SkillNormalizer) -> bool:
    if not validate_skill_for_matching(raw)[0]:
        return False
    text = normalize_skill_text(raw)
    if is_process_skill_name(text):
        return False
    if not is_technical_skill(text):
        return False
    return normalizer.resolve_canonical(text) is None


def _is_report_noise(skill: str) -> bool:
    text = skill.strip()
    if not text:
        return True
    for pattern in _OOV_REPORT_NOISE_RES:
        if pattern.search(text):
            return True
    return False


def _is_valid_oov_skill(skill: str, normalizer: SkillNormalizer) -> bool:
    if len(skill) < 2 or len(skill) > 80:
        return False
    if _is_report_noise(skill):
        return False
    if not validate_skill_for_matching(skill)[0]:
        return False
    if not is_technical_skill(skill):
        return False
    return _is_oov_token(skill, normalizer)


def _add(counter: Counter[str], sources: dict[str, set[str]], skill: str, source: str, normalizer: SkillNormalizer) -> None:
    skill = skill.strip()
    if not skill or not _is_valid_oov_skill(skill, normalizer):
        return
    counter[skill] += 1
    sources[skill].add(source)


def _collect_from_match_results(
    path: Path,
    since: datetime,
    counter: Counter[str],
    sources: dict[str, set[str]],
    normalizer: SkillNormalizer,
) -> None:
    if not path.exists():
        return
    seen_case_skill: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_ts(str(row.get("ts", "")))
            if ts and ts < since:
                continue
            case_id = str(row.get("case_id", ""))
            for reason in row.get("reasons") or []:
                m = UNKNOWN_REASON_RE.search(str(reason))
                if not m:
                    continue
                for skill in _split_skills(m.group(1)):
                    skill = skill.strip()
                    pair = (case_id, skill)
                    if pair in seen_case_skill:
                        continue
                    seen_case_skill.add(pair)
                    _add(counter, sources, skill, "案件", normalizer)


def _collect_from_unknown_candidates(
    dir_path: Path,
    since_date: datetime.date,
    counter: Counter[str],
    sources: dict[str, set[str]],
    normalizer: SkillNormalizer,
) -> None:
    if not dir_path.exists():
        return
    for fp in sorted(dir_path.glob("*.json")):
        try:
            file_date = datetime.strptime(fp.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if file_date < since_date:
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        for item in data.get("candidates") or []:
            skill = str(item.get("skill", "")).strip()
            count = int(item.get("count") or 1)
            if skill and _is_valid_oov_skill(skill, normalizer):
                counter[skill] += count
                sources[skill].add("案件")


def _collect_from_logs(
    log_dir: Path,
    since_date: datetime.date,
    counter: Counter[str],
    sources: dict[str, set[str]],
    normalizer: SkillNormalizer,
) -> None:
    patterns = [
        (log_dir / "matching_v3_*.log", UNKNOWN_REASON_RE, "案件"),
        (log_dir / "realtime_match_worker.log", UNKNOWN_EVIDENCE_RE, "人材"),
    ]
    for glob_pat, pattern, source in patterns:
        for fp in sorted(log_dir.glob(glob_pat.name)):
            if "matching_v3_" in fp.name:
                try:
                    d = datetime.strptime(fp.name.split("_")[-1].replace(".log", ""), "%Y%m%d").date()
                    if d < since_date:
                        continue
                except ValueError:
                    pass
            text = fp.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if pattern is UNKNOWN_REASON_RE:
                    m = pattern.search(line)
                    if m:
                        for skill in _split_skills(m.group(1)):
                            _add(counter, sources, skill, source, normalizer)
                elif pattern is UNKNOWN_EVIDENCE_RE:
                    m = pattern.search(line)
                    if m:
                        try:
                            items = ast.literal_eval(m.group(1))
                        except (SyntaxError, ValueError):
                            continue
                        for skill in items:
                            _add(counter, sources, str(skill), source, normalizer)


def _collect_from_structured(
    path: Path,
    recent_case_ids: set[str],
    counter: Counter[str],
    sources: dict[str, set[str]],
    normalizer: SkillNormalizer,
) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            case_id = str(row.get("case_id", ""))
            if recent_case_ids and case_id not in recent_case_ids:
                continue
            for bucket in ("required_skills", "optional_skills", "ambiguous_skills"):
                for skill in row.get(bucket) or []:
                    raw = str(skill).strip()
                    if _is_oov_token(raw, normalizer):
                        _add(counter, sources, raw, "案件", normalizer)


def _collect_from_engineers(
    path: Path,
    counter: Counter[str],
    sources: dict[str, set[str]],
    normalizer: SkillNormalizer,
) -> None:
    if not path.exists():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return
    for eng in data:
        raw_skills = eng.get("skills") or eng.get("スキル") or []
        if isinstance(raw_skills, str):
            raw_skills = [s.strip() for s in re.split(r"[,、/|]", raw_skills) if s.strip()]
        for skill in raw_skills:
            raw = str(skill).strip()
            if _is_oov_token(raw, normalizer):
                _add(counter, sources, raw, "人材", normalizer)


def _recent_case_ids(match_results: Path, since: datetime) -> set[str]:
    ids: set[str] = set()
    if not match_results.exists():
        return ids
    with match_results.open(encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = _parse_ts(str(row.get("ts", "")))
            if ts and ts >= since:
                cid = row.get("case_id")
                if cid:
                    ids.add(str(cid))
    return ids


def write_report(counter: Counter[str], sources: dict[str, set[str]]) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []
    for skill, count in counter.most_common():
        src = "/".join(sorted(sources[skill]))
        rows.append((skill, count, src))
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["skill", "count", "source"])
        writer.writerows(rows)
    return rows


def append_top100_to_tasks(rows: list[tuple[str, int, str]]) -> None:
    top = rows[:100]
    block_lines = [
        "",
        "## OOV Top 100（2026-07-03 調査）",
        "",
        "| # | スキル語 | 出現回数 | 出現元 |",
        "|---|---------|---------|--------|",
    ]
    for i, (skill, count, source) in enumerate(top, 1):
        block_lines.append(f"| {i} | {skill} | {count} | {source} |")
    block_lines.append("")

    text = TASKS_MD.read_text(encoding="utf-8") if TASKS_MD.exists() else ""
    marker = "## OOV Top 100（2026-07-03 調査）"
    if marker in text:
        before = text.split(marker)[0].rstrip()
        TASKS_MD.write_text(before + "\n".join(block_lines), encoding="utf-8")
    else:
        TASKS_MD.write_text(text.rstrip() + "\n" + "\n".join(block_lines), encoding="utf-8")


def main() -> int:
    now = datetime.now(JST)
    since = now - timedelta(days=30)
    since_date = since.date()

    normalizer = SkillNormalizer(BASE_DIR / "skill_aliases.json")
    counter: Counter[str] = Counter()
    sources: dict[str, set[str]] = defaultdict(set)

    match_results = BASE_DIR / "logs" / "match_results.jsonl"
    recent_ids = _recent_case_ids(match_results, since)

    _collect_from_match_results(match_results, since, counter, sources, normalizer)
    _collect_from_unknown_candidates(
        SES_WORK / "logs" / "unknown_skill_candidates",
        since_date,
        counter,
        sources,
        normalizer,
    )
    _collect_from_logs(BASE_DIR / "logs", since_date, counter, sources, normalizer)
    _collect_from_structured(
        BASE_DIR / "logs" / "structured.jsonl",
        recent_ids,
        counter,
        sources,
        normalizer,
    )
    _collect_from_engineers(SES_WORK / "poc_engineers.json", counter, sources, normalizer)

    rows = write_report(counter, sources)
    append_top100_to_tasks(rows)
    print(f"oov_report.csv: {len(rows)} skills")
    print(f"TASKS.md: top {min(100, len(rows))} appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
