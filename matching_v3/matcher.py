from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
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


def calc_gross_profit(case_rate: float, engineer_rate: float) -> float:
    """粗利計算（単位: 万円）"""
    return case_rate - engineer_rate


def meets_profit_floor(case_rate: float, engineer_rate: float, floor_man: float = 5.0) -> bool:
    """最低粗利チェック。floor_man は万円単位（デフォルト5万円）。"""
    return calc_gross_profit(case_rate, engineer_rate) >= floor_man


def _engineer_last_updated_str(engineer: dict) -> str | None:
    for key in ("最終更新日", "last_updated", "_last_edited_time"):
        value = engineer.get(key)
        if value:
            return str(value)
    return None


def is_engineer_fresh(engineer: dict, threshold_days: int = ENGINEER_STALENESS_DAYS) -> bool:
    """人材情報の鮮度チェック。最終更新から threshold_days 日以内なら True。"""
    last_updated_str = _engineer_last_updated_str(engineer)
    if not last_updated_str:
        return False
    try:
        text = last_updated_str.replace("Z", "+00:00")
        last_updated = datetime.fromisoformat(text)
        now = datetime.now(timezone.utc)
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        else:
            last_updated = last_updated.astimezone(timezone.utc)
        return (now - last_updated).days <= threshold_days
    except (ValueError, TypeError):
        return False


def _actual_price(value) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _case_search_text(case_json: dict) -> str:
    parts = [str(skill) for skill in (case_json.get("required_skills") or [])]
    job_description = case_json.get("job_description") or ""
    return " ".join(parts + [job_description])


def _engineer_search_text(engineer: dict) -> str:
    return " ".join(str(skill) for skill in (engineer.get("スキル") or []))


def _estimate_case_price(case_json: dict) -> float:
    text = _case_search_text(case_json)
    years = case_json.get("experience_years")
    years_val = float(years) if years is not None else None

    if years_val is not None and years_val >= 5:
        if _contains_any(text, ["要件定義", "基本設計"]):
            return 80.0
        if _contains_any(text, ["基本設計", "詳細設計"]):
            return 70.0
    if years_val is not None and years_val >= 3:
        if _contains_any(text, ["詳細設計", "製造", "実装"]):
            return 60.0
    return 50.0


def _estimate_engineer_price(engineer: dict) -> float:
    text = _engineer_search_text(engineer)
    years = engineer.get("経験年数")
    years_val = float(years) if years is not None else None

    if years_val is not None and years_val >= 5:
        if _contains_any(text, ["要件定義", "基本設計"]):
            return 75.0
        if _contains_any(text, ["基本設計", "詳細設計"]):
            return 65.0
    if years_val is not None and years_val >= 3:
        if _contains_any(text, ["詳細設計", "製造", "実装"]):
            return 55.0
    return 45.0


def judge(
    case_json: dict,
    engineer: dict,
    normalizer: SkillNormalizer,
    assignee: str | None = None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    eng_actual = _actual_price(engineer.get("単価（万円）"))
    case_actual = _actual_price(case_json.get("price_max"))
    if eng_actual is not None:
        eng_price = eng_actual
    else:
        eng_price = _estimate_engineer_price(engineer)
        reasons.append(f"エンジニア単価推定: {eng_price}万")
    if case_actual is not None:
        case_max = case_actual
    else:
        case_max = _estimate_case_price(case_json)
        reasons.append(f"案件単価推定: {case_max}万（スキル見合い案件）")

    floor = _gross_threshold(assignee or case_json.get("担当者"))
    if not meets_profit_floor(case_max, eng_price, floor):
        gross = calc_gross_profit(case_max, eng_price)
        return "NG", [f"粗利不足: {gross}万円 < 最低粗利{int(floor)}万円"]

    required_raw = case_json.get("required_skills") or []
    eng_skills_raw = engineer.get("スキル") or []
    eng_skills = set()
    for skill in eng_skills_raw:
        normalized = normalizer.normalize(skill)
        eng_skills.add(normalized if normalized else skill)
    missing = []
    for skill in required_raw:
        normalized = normalizer.normalize(skill)
        if normalized and normalized not in eng_skills:
            missing.append(normalized)
    if missing:
        return "NG", [f"必須スキル不足: {missing}"]

    p_score = _calc_parallel_score(engineer)
    if p_score >= 5.0:
        return "NG", [f"並行過多: スコア{p_score:.1f}（上限5.0）"]

    if not is_engineer_fresh(engineer):
        last_edit = _engineer_last_updated_str(engineer)
        if last_edit:
            reasons.append(f"エンジニア情報古い（{_days_since(last_edit)}日前更新）")
        else:
            reasons.append("エンジニア情報古い（最終更新日不明）")

    if case_json.get("ambiguous_skills"):
        reasons.append(f"曖昧スキルあり: {case_json['ambiguous_skills']}")

    conf = float(case_json.get("extraction_confidence", 1.0) or 0.0)
    if conf < 0.3:
        reasons.append(f"構造化精度低: {conf:.2f}")

    if reasons:
        non_ambig = [r for r in reasons if not r.startswith("曖昧スキルあり")]
        if not non_ambig:
            return "NG", ["曖昧スキルのみ: 判定不可"]
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


def _parse_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _score_result_waiting(days_waiting: int) -> float:
    if days_waiting <= 2:
        return 2.5
    if days_waiting <= 7:
        return 2.0
    return 0.0


def _calc_parallel_score(engineer: dict, *, today: date | None = None) -> float:
    reference = today or date.today()
    parallel_items = engineer.get("並行案件") or engineer.get("parallel_items") or []
    if parallel_items:
        score = 0.0
        for parallel in parallel_items:
            status = str(parallel.get("ステータス") or parallel.get("status") or "")
            if status == "オファー中":
                score += 5.0
            elif status == "面談予定":
                score += 2.0
            elif status == "面談調整中":
                score += 1.5
            elif status == "結果待ち":
                interview_date = _parse_date(parallel.get("面談日"))
                if interview_date is None:
                    score += 1.0
                else:
                    days_waiting = (reference - interview_date).days
                    score += _score_result_waiting(days_waiting)
        return score

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
    return not is_engineer_fresh(engineer)


def filter_fresh_engineers(
    engineers: list[dict],
    log: logging.Logger | None = None,
) -> list[dict]:
    """21日超の人材をマッチング対象から除外し、除外分をログに記録する。"""
    active_logger = log or logger
    fresh: list[dict] = []
    for engineer in engineers:
        if is_engineer_fresh(engineer):
            fresh.append(engineer)
            continue
        name = engineer.get("名前", engineer.get("id", ""))
        last_edit = _engineer_last_updated_str(engineer)
        if not last_edit:
            active_logger.info("stale: %s (最終更新日不明)", name)
        else:
            active_logger.info("stale: %s (%d日経過)", name, _days_since(last_edit))
    return fresh
