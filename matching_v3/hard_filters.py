"""Rule-based hard filters applied before LLM/rule judge in matching_v3."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import structurer
from config import HARD_FILTERS
from matcher import SkillNormalizer

PRICE_BUFFER_MAN = 3


@dataclass
class CaseView:
    rate_max_man: float | None = None
    rate_type: str | None = None
    remote_type: str | None = None
    location_area: str | None = None
    required_skills: list[str] = field(default_factory=list)
    start_date: date | None = None


@dataclass
class EngineerView:
    desired_rate_min: float | None = None
    commutable_areas: set[str] = field(default_factory=set)
    skills: list[str] = field(default_factory=list)
    available_date: date | None = None


@dataclass
class FilterDropStats:
    total_in: int = 0
    total_out: int = 0
    dropped_rate: int = 0
    dropped_remote_location: int = 0
    dropped_skill_threshold: int = 0
    dropped_start_timing: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "total_in": self.total_in,
            "total_out": self.total_out,
            "dropped_rate": self.dropped_rate,
            "dropped_remote_location": self.dropped_remote_location,
            "dropped_skill_threshold": self.dropped_skill_threshold,
            "dropped_start_timing": self.dropped_start_timing,
        }


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("/", "-")
    for size in (10, 7):
        try:
            return date.fromisoformat(normalized[:size])
        except ValueError:
            continue
    return None


def _coerce_rate_man(value: Any) -> float | None:
    if value is None:
        return None
    try:
        rate = float(value)
    except (TypeError, ValueError):
        return None
    if rate > 200:
        return None
    return rate


def _normalize_remote_type(case: dict[str, Any], case_json: dict[str, Any]) -> str | None:
    remote = case.get("remote_type") or case_json.get("remote_type")
    if remote:
        return str(remote)
    legacy = str(case.get("リモート") or "").strip()
    if legacy in ("フルリモート", "リモート"):
        return "full_remote"
    if legacy in ("一部リモート", "ハイブリッド"):
        return "hybrid"
    if legacy in ("常駐", "出社"):
        return "onsite"
    remote_ok = str(case_json.get("remote_ok") or "").lower()
    if remote_ok == "full":
        return "full_remote"
    if remote_ok == "partial":
        return "hybrid"
    if remote_ok == "none":
        return "onsite"
    return None


def build_case_view(case: dict[str, Any], case_json: dict[str, Any]) -> CaseView:
    rate_max = _coerce_rate_man(case_json.get("price_max"))
    if rate_max is None:
        rate_max = _coerce_rate_man(case.get("単価（万円）") or case.get("単価"))

    location_raw = (
        case.get("勤務地")
        or case_json.get("work_location")
        or case_json.get("location_normalized")
        or case_json.get("location")
    )
    _, location_area = structurer.normalize_location_text(str(location_raw) if location_raw else None)

    return CaseView(
        rate_max_man=rate_max,
        rate_type=case.get("rate_type") or case_json.get("rate_type"),
        remote_type=_normalize_remote_type(case, case_json),
        location_area=location_area,
        required_skills=list(case_json.get("required_skills") or []),
        start_date=_parse_date(case_json.get("start_date")),
    )


def build_engineer_view(engineer: dict[str, Any]) -> EngineerView:
    residence = str(engineer.get("居住地") or "").strip()
    _, normalized_residence = structurer.normalize_location_text(residence) if residence else (None, None)
    commutable = set()
    if normalized_residence:
        commutable.add(normalized_residence)
    elif residence:
        commutable.add(residence)

    skills = list(engineer.get("正規化スキル") or engineer.get("スキル") or [])
    available = _parse_date(engineer.get("稼働可能日") or engineer.get("稼働開始"))

    return EngineerView(
        desired_rate_min=_coerce_rate_man(engineer.get("単価（万円）") or engineer.get("単価")),
        commutable_areas=commutable,
        skills=skills,
        available_date=available,
    )


def rate_compatible(case: CaseView, engineer: EngineerView) -> bool:
    if case.rate_max_man is None:
        return True
    if case.rate_type == "skill_dependent_no_number":
        return True
    if engineer.desired_rate_min is None:
        return True
    return engineer.desired_rate_min <= case.rate_max_man + PRICE_BUFFER_MAN


def location_compatible(case: CaseView, engineer: EngineerView) -> bool:
    if case.remote_type in (None, "unknown", "full_remote"):
        return True
    if not engineer.commutable_areas:
        return True
    if not case.location_area:
        return True
    return case.location_area in engineer.commutable_areas


def _normalize_skill_set(skills: list[str], normalizer: SkillNormalizer) -> set[str]:
    out: set[str] = set()
    for skill in skills:
        canonical = normalizer.resolve_canonical(str(skill))
        if canonical:
            out.add(canonical)
            continue
        hard = normalizer.normalize_hard(str(skill))
        if hard:
            out.add(hard)
    return out


def skill_compatible(case: CaseView, engineer: EngineerView, normalizer: SkillNormalizer) -> bool:
    if not case.required_skills:
        return True
    required = _normalize_skill_set(case.required_skills, normalizer)
    if not required:
        return True
    engineer_skills = _normalize_skill_set(engineer.skills, normalizer)
    overlap = required & engineer_skills
    if len(required) == 1:
        return len(overlap) >= 1
    return len(overlap) / len(required) >= 0.5


def start_timing_compatible(case: CaseView, engineer: EngineerView) -> bool:
    if case.start_date is None:
        return True
    if engineer.available_date is None:
        return True
    case_month = (case.start_date.year, case.start_date.month)
    eng_month = (engineer.available_date.year, engineer.available_date.month)
    return eng_month <= case_month


def apply_hard_filters(
    case: dict[str, Any],
    case_json: dict[str, Any],
    engineers: list[dict[str, Any]],
    normalizer: SkillNormalizer,
    filters: dict[str, bool] | None = None,
) -> tuple[list[dict[str, Any]], FilterDropStats]:
    """Apply enabled hard filters and return surviving engineers + drop stats."""
    active = filters if filters is not None else HARD_FILTERS
    case_view = build_case_view(case, case_json)
    stats = FilterDropStats(total_in=len(engineers))
    survivors: list[dict[str, Any]] = []

    for engineer in engineers:
        eng_view = build_engineer_view(engineer)
        if active.get("rate", True) and not rate_compatible(case_view, eng_view):
            stats.dropped_rate += 1
            continue
        if active.get("remote_location", True) and not location_compatible(case_view, eng_view):
            stats.dropped_remote_location += 1
            continue
        if active.get("skill_threshold", True) and not skill_compatible(case_view, eng_view, normalizer):
            stats.dropped_skill_threshold += 1
            continue
        if active.get("start_timing", True) and not start_timing_compatible(case_view, eng_view):
            stats.dropped_start_timing += 1
            continue
        survivors.append(engineer)

    stats.total_out = len(survivors)
    return survivors, stats
