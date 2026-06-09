from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path


logger = logging.getLogger(__name__)
ENGINEER_STALENESS_DAYS = 21
GROSS_THRESHOLDS = {"松野": 5, "岡本": 3}


class SkillNormalizer:
    def __init__(self, aliases_path: str | Path) -> None:
        with Path(aliases_path).open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.hard = {k.lower(): v for k, v in data["aliases"].items()}
        self.soft = {k.lower(): v for k, v in data["soft_aliases"].items()}
        self.soft_enabled = data.get("soft_aliases_enabled", False)

    def normalize(self, skill: str) -> str | None:
        key = " ".join(skill.lower().strip().split())
        if key in self.hard:
            return self.hard[key]
        if self.soft_enabled and key in self.soft:
            return self.soft[key]
        return None


def _gross_threshold(assignee: str | None) -> float:
    return float(GROSS_THRESHOLDS.get(assignee or "", 5))


def judge(
    case_json: dict,
    engineer: dict,
    normalizer: SkillNormalizer,
    assignee: str | None = None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    eng_price = float(engineer.get("単価（万円）") or 0)
    case_max = float(case_json.get("price_max") or 0)
    if not case_max or not eng_price:
        reasons.append("単価情報不足（確認要）")
    else:
        gross = case_max - eng_price
        floor = _gross_threshold(assignee or case_json.get("担当者"))
        if gross < floor:
            return "NG", [f"粗利不足: {gross}万円 < {int(floor)}万円"]

    required_raw = case_json.get("required_skills") or []
    eng_skills_raw = engineer.get("スキル") or []
    eng_skills = set()
    for skill in eng_skills_raw:
        normalized = normalizer.normalize(skill)
        eng_skills.add(normalized if normalized else skill)
    missing = []
    for skill in required_raw:
        normalized = normalizer.normalize(skill)
        if normalized is None:
            reasons.append(f"未登録必須スキル要確認: {skill}")
        elif normalized not in eng_skills:
            missing.append(normalized)
    if missing:
        return "NG", [f"必須スキル不足: {missing}"]

    p_score = _calc_parallel_score(engineer)
    if p_score >= 5.0:
        return "NG", [f"並行過多: スコア{p_score:.1f}（上限5.0）"]

    last_edit = engineer.get("_last_edited_time", "")
    if last_edit and _days_since(last_edit) > ENGINEER_STALENESS_DAYS:
        reasons.append(f"エンジニア情報古い（{_days_since(last_edit)}日前更新）")

    if case_json.get("ambiguous_skills"):
        reasons.append(f"曖昧スキルあり: {case_json['ambiguous_skills']}")

    conf = float(case_json.get("extraction_confidence", 1.0) or 0.0)
    if conf < 0.3:
        reasons.append(f"構造化精度低: {conf:.2f}")

    if reasons:
        non_ambig = [r for r in reasons if not r.startswith("曖昧スキルあり")]
        if not non_ambig:
            return "REVIEW", reasons
        return "REVIEW", reasons
    return "MATCH", []


def optional_skill_bonus_ok(case_json: dict, engineer: dict, normalizer: SkillNormalizer) -> bool:
    optional_raw = case_json.get("optional_skills") or []
    if not optional_raw:
        return False
    eng_skills = set(engineer.get("スキル") or [])
    normalized = [normalizer.normalize(skill) for skill in optional_raw]
    comparable = [skill for skill in normalized if skill]
    if not comparable:
        return False
    owned = sum(1 for skill in comparable if skill in eng_skills)
    return owned / len(comparable) >= 0.5


def _calc_parallel_score(engineer: dict) -> float:
    memo = engineer.get("備考（LINEメモ）") or ""
    score = 0.0
    if "オファー中" in memo or "offer" in memo.lower():
        score += 5.0
    if "面談予定" in memo:
        score += 2.0
    if "面談調整中" in memo:
        score += 1.5
    if "結果待ち" in memo:
        score += 2.0
    return score


def _days_since(iso_str: str) -> int:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return delta.days
    except Exception:
        return 0


def is_stale_engineer(engineer: dict) -> bool:
    last_edit = engineer.get("_last_edited_time", "")
    if not last_edit:
        return False
    return _days_since(last_edit) > ENGINEER_STALENESS_DAYS


def filter_fresh_engineers(
    engineers: list[dict],
    log: logging.Logger | None = None,
) -> list[dict]:
    """21日超の人材をマッチング対象から除外し、除外分をログに記録する。"""
    active_logger = log or logger
    fresh: list[dict] = []
    for engineer in engineers:
        last_edit = engineer.get("_last_edited_time", "")
        if not last_edit:
            fresh.append(engineer)
            continue
        days = _days_since(last_edit)
        if days > ENGINEER_STALENESS_DAYS:
            active_logger.info(
                "stale: %s (%d日経過)",
                engineer.get("名前", engineer.get("id", "")),
                days,
            )
            continue
        fresh.append(engineer)
    return fresh
