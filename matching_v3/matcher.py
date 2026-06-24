from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from staleness_checker import STALENESS_DAYS
from staleness_checker import check as staleness_check

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


logger = logging.getLogger(__name__)
ENGINEER_STALENESS_DAYS = STALENESS_DAYS
GROSS_THRESHOLDS = {"松野": 5, "岡本": 3}
UNIT_PRICE_REVIEW_TAG = "【単価REVIEW】"
ENGINEER_MEMO_FIELD = "備考（LINEメモ）"
_SOFT_SKILLS_PATH = Path(__file__).resolve().parent.parent / "config" / "soft_skills.json"
_PROCESS_SKILLS_PATH = Path(__file__).resolve().parent.parent / "config" / "process_skills.json"
_soft_skills_cache: set[str] | None = None
_process_skills_cache: set[str] | None = None


def _load_soft_skill_set() -> set[str]:
    global _soft_skills_cache
    if _soft_skills_cache is None:
        with _SOFT_SKILLS_PATH.open(encoding="utf-8") as f:
            items = json.load(f)
        _soft_skills_cache = {" ".join(str(skill).lower().strip().split()) for skill in items if str(skill).strip()}
    return _soft_skills_cache


def _load_process_skill_set() -> set[str]:
    global _process_skills_cache
    if _process_skills_cache is None:
        with _PROCESS_SKILLS_PATH.open(encoding="utf-8") as f:
            items = json.load(f)
        _process_skills_cache = {str(skill).strip() for skill in items if str(skill).strip()}
    return _process_skills_cache


def _is_soft_skill(skill: str) -> bool:
    key = " ".join(skill.lower().strip().split())
    if not key:
        return False
    soft_set = _load_soft_skill_set()
    if key in soft_set:
        return True
    return any(token in key for token in soft_set if len(token) >= 2)


def _is_process_skill(skill: str) -> bool:
    text = skill.strip()
    if not text:
        return False
    return text in _load_process_skill_set()


def _without_soft_skills(skills: list[str]) -> list[str]:
    return [skill for skill in skills if not _is_soft_skill(skill)]


CAPABILITY_RE = re.compile(
    r".*(?:経験|経験者|可能|以上|知識|スキル|対応力|管理能力)$"
)
CAPABILITY_CONTAINS_RE = re.compile(r".*できる.*")
UNKNOWN_MATCH_RATIO_THRESHOLD = 0.3
STRICT_FUZZY_MAX_LEN = 3


def _is_capability_skill(skill: str) -> bool:
    text = skill.strip()
    if not text:
        return False
    if CAPABILITY_RE.match(text):
        return True
    return bool(CAPABILITY_CONTAINS_RE.match(text))


def _without_capabilities(skills: list[str]) -> tuple[list[str], list[str]]:
    technical: list[str] = []
    competencies: list[str] = []
    for skill in skills:
        if _is_capability_skill(skill) or _is_process_skill(skill):
            competencies.append(skill)
        else:
            technical.append(skill)
    return technical, competencies


def _partition_required_skills(skills: list[str]) -> tuple[list[str], list[str]]:
    return _without_capabilities(skills)


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text))
    normalized = normalized.lower().strip()
    return re.sub(r"[\s\u3000]+", "", normalized)


def _strip_vendor_prefix(text: str) -> str:
    for prefix in ("aws", "azure", "gcp", "google", "microsoft", "ms"):
        if text.startswith(prefix) and len(text) > len(prefix):
            return text[len(prefix):]
    return text


def _fuzzy_query_variants(query: str) -> list[str]:
    normalized = _normalize_text(query)
    if not normalized:
        return []
    variants = [normalized]
    stripped = _strip_vendor_prefix(normalized)
    if stripped not in variants:
        variants.append(stripped)
    return variants


def _is_strict_fuzzy_query(query: str, strict_keys: set[str]) -> bool:
    key = " ".join(query.lower().strip().split())
    normalized = _normalize_text(query)
    return len(normalized) <= STRICT_FUZZY_MAX_LEN or key in strict_keys


def _fuzzy_match(query: str, eng_skills: list[str], *, strict_keys: set[str] | None = None) -> bool:
    if not _normalize_text(query):
        return False
    strict = strict_keys or set()
    exact_only = _is_strict_fuzzy_query(query, strict)
    for skill in eng_skills:
        s = _normalize_text(skill)
        if not s:
            continue
        for q in _fuzzy_query_variants(query):
            if q == s:
                return True
            if exact_only:
                continue
            if q in s:
                return True
            if s in q and len(q) - len(s) <= 2:
                return True
    return False


def _dedupe_required_by_parent(
    required: list[str],
    normalizer: SkillNormalizer,
) -> list[str]:
    parent_skills = normalizer.parent_skills
    if not parent_skills:
        return required
    parents_in_list = {
        canonical
        for skill in required
        if (canonical := normalizer.normalize_hard(skill) or skill.strip())
    }
    child_canonicals_to_drop = {
        child for child, parent in parent_skills.items() if parent in parents_in_list
    }
    if not child_canonicals_to_drop:
        return required
    return [
        skill
        for skill in required
        if (normalizer.normalize_hard(skill) or skill.strip()) not in child_canonicals_to_drop
    ]


def _engineer_has_canonical(canonical: str, eng_skills: set[str], parent_skills: dict[str, str]) -> bool:
    if canonical in eng_skills:
        return True
    return any(child in eng_skills and parent == canonical for child, parent in parent_skills.items())


class SkillNormalizer:
    def __init__(self, aliases_path: str | Path) -> None:
        with Path(aliases_path).open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.hard = {k.lower(): v for k, v in data["aliases"].items()}
        self.soft = {k.lower(): v for k, v in data["soft_aliases"].items()}
        self.soft_enabled = data.get("soft_aliases_enabled", False)
        self.strict_keys = {key.lower() for key in data.get("strict_alias_keys", [])}
        self.parent_skills = dict(data.get("parent_skills", {}))
        self.skill_tiers = {str(k): int(v) for k, v in data.get("skill_tiers", {}).items()}
        canonicals: set[str] = set(data.get("canonical_skills", []))
        canonicals.update(self.hard.values())
        canonicals.update(self.skill_tiers)
        self._canonicals = sorted(canonicals, key=len, reverse=True)
        alias_pairs: list[tuple[str, str]] = []
        for alias, canonical in data["aliases"].items():
            alias_pairs.append((alias, canonical))
        if self.soft_enabled:
            for alias, canonical in data.get("soft_aliases", {}).items():
                alias_pairs.append((alias, canonical))
        self._alias_pairs = sorted(alias_pairs, key=lambda item: len(item[0]), reverse=True)

    def skill_tier(self, canonical: str) -> int:
        return int(self.skill_tiers.get(canonical, 1))

    def _skill_key(self, skill: str) -> str:
        return " ".join(skill.lower().strip().split())

    def normalize_hard(self, skill: str) -> str | None:
        key = self._skill_key(skill)
        if key in self.hard:
            return self.hard[key]
        return None

    def normalize_soft(self, skill: str) -> str | None:
        key = self._skill_key(skill)
        if key in self.hard:
            return self.hard[key]
        if self.soft_enabled and key in self.soft:
            return self.soft[key]
        return None

    def normalize(self, skill: str) -> str | None:
        return self.normalize_hard(skill)

    def resolve_canonical(self, skill: str) -> str | None:
        """hard/softエイリアスに無い場合もtier登録済みcanonical名はそのまま解決する。"""
        hard = self.normalize_hard(skill)
        if hard:
            return hard
        key = self._skill_key(skill)
        if self.soft_enabled and key in self.soft:
            return self.soft[key]
        for canon in self.skill_tiers:
            if canon.lower() == key:
                return canon
        return None

    def all_canonicals(self) -> list[str]:
        return list(self._canonicals)

    def all_aliases(self) -> list[tuple[str, str]]:
        return list(self._alias_pairs)


def canonicalize_skill_list(skills: list[str], normalizer: SkillNormalizer) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        resolved = normalizer.resolve_canonical(str(skill)) or str(skill).strip()
        if resolved and resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return result


def extract_skills_from_text(text: str, normalizer: SkillNormalizer) -> list[str]:
    """案件名/詳細テキストから canonical・alias をルールベースで抽出する。"""
    if not text or not text.strip():
        return []
    lowered = text.lower()
    found: list[str] = []
    seen: set[str] = set()
    for canonical in normalizer.all_canonicals():
        if canonical.lower() in lowered and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    for alias, canonical in normalizer.all_aliases():
        if alias.lower() in lowered and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


def resolve_case_required_skills(
    case: dict[str, Any],
    case_json: dict[str, Any],
    normalizer: SkillNormalizer,
) -> tuple[list[str], str]:
    """Notion案件の必須スキルを解決する。空なら案件名→詳細→原文の順でフォールバック。"""
    notion_skills = case.get("必要スキル") or []
    if notion_skills:
        return canonicalize_skill_list([str(s) for s in notion_skills], normalizer), "multi_select"

    for source, field in (
        ("fallback_title", "案件名"),
        ("fallback_detail", "案件詳細"),
        ("fallback_original", "案件情報原文"),
    ):
        text = str(case.get(field) or "")
        found = extract_skills_from_text(text, normalizer)
        if found:
            return found, source

    struct_skills = case_json.get("required_skills") or []
    if struct_skills:
        return canonicalize_skill_list([str(s) for s in struct_skills], normalizer), "structurer"

    return [], "none"


def prepare_engineer_skills(engineer: dict[str, Any], normalizer: SkillNormalizer) -> dict[str, Any]:
    """multi_select「スキル」を正規化し、正規化スキルが空なら補完する。"""
    raw = engineer.get("スキル") or []
    if not raw:
        return engineer
    normalized = canonicalize_skill_list([str(s) for s in raw], normalizer)
    if not normalized:
        return engineer
    if engineer.get("正規化スキル"):
        return engineer
    return {**engineer, "正規化スキル": normalized}


def log_case_skills_debug(
    case_id: str,
    required_skills: list[str],
    source: str,
    *,
    logger: logging.Logger | None = None,
) -> None:
    log = logger or logging.getLogger(__name__)
    log.debug(
        "case=%s required_skills=%s source=%s",
        case_id,
        required_skills,
        source,
    )


def log_engineer_match_debug(
    engineer: dict[str, Any],
    *,
    logger: logging.Logger | None = None,
) -> None:
    log = logger or logging.getLogger(__name__)
    eng_label = engineer.get("名前") or engineer.get("id") or "?"
    skills = engineer.get("正規化スキル") or engineer.get("スキル") or []
    price = engineer.get("単価（万円）") or engineer.get("単価")
    log.debug("eng=%s skills=%s price=%s", eng_label, skills, price)


def log_match_debug(
    case_id: str,
    required_skills: list[str],
    source: str,
    engineer: dict[str, Any],
    *,
    logger: logging.Logger | None = None,
) -> None:
    log_case_skills_debug(case_id, required_skills, source, logger=logger)
    log_engineer_match_debug(engineer, logger=logger)


def _gross_threshold(assignee: str | None) -> float:
    return float(GROSS_THRESHOLDS.get(assignee or "", 5))


def calc_gross_profit(case_rate: float, engineer_rate: float) -> float:
    """粗利計算（単位: 万円）"""
    return case_rate - engineer_rate


def meets_profit_floor(case_rate: float, engineer_rate: float, floor_man: float = 5.0) -> bool:
    """最低粗利チェック。floor_man は万円単位（デフォルト5万円）。"""
    return calc_gross_profit(case_rate, engineer_rate) >= floor_man


def _engineer_staleness_source(engineer: dict) -> tuple[str, int]:
    result = staleness_check(engineer)
    source = result.get("source_field", "missing")
    days_old = int(result.get("days_old", -1))
    if source == "情報取得日":
        value = engineer.get("情報取得日")
    elif source == "last_edited_time":
        value = engineer.get("_last_edited_time") or engineer.get("last_edited_time")
    else:
        value = None
    return str(value or ""), days_old


def is_engineer_fresh(engineer: dict, threshold_days: int = ENGINEER_STALENESS_DAYS) -> bool:
    """人材情報の鮮度チェック。staleness_checker に委譲する。"""
    return staleness_check(engineer, max_days=threshold_days)["is_fresh"]


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


def build_skill_index(
    engineers: list[dict],
    normalizer: SkillNormalizer,
) -> dict[str, set[str]]:
    """skill canonical -> engineer_id の逆引きインデックス。"""
    index: dict[str, set[str]] = {}
    for engineer in engineers:
        engineer_id = engineer.get("id")
        if not engineer_id:
            continue
        for skill in engineer.get("正規化スキル") or engineer.get("スキル") or []:
            canonical = normalizer.resolve_canonical(str(skill)) or str(skill).strip()
            if not canonical:
                continue
            index.setdefault(canonical, set()).add(engineer_id)
    return index


def filter_engineers_by_required_skills(
    engineers: list[dict],
    normalizer: SkillNormalizer,
    skill_index: dict[str, set[str]],
    required_skills: list[str],
) -> list[dict]:
    """required_skillsで候補エンジニアを絞り込む。空なら全件。"""
    if not required_skills:
        return engineers
    candidate_ids: set[str] | None = None
    resolved_count = 0
    for skill in required_skills:
        canonical = normalizer.resolve_canonical(skill)
        if not canonical:
            continue
        resolved_count += 1
        skill_ids = skill_index.get(canonical, set())
        candidate_ids = skill_ids if candidate_ids is None else candidate_ids & skill_ids
    if resolved_count == 0:
        return engineers
    if not candidate_ids:
        return []
    return [engineer for engineer in engineers if engineer.get("id") in candidate_ids]


def _classify_required_hit(
    req_skill: str,
    canonical: str,
    eng_skills_raw: list[str],
    normalizer: SkillNormalizer,
) -> str:
    """必須スキル充足の一致種別: exact / alias / soft_alias。"""
    req_key = normalizer._skill_key(req_skill)
    req_hard = normalizer.normalize_hard(req_skill)
    req_soft = normalizer.normalize_soft(req_skill) if req_hard is None else None
    if req_hard is None and req_soft is not None and req_key in normalizer.soft:
        return "soft_alias"

    saw_exact = False
    saw_alias = False
    saw_soft = False
    for eng_skill in eng_skills_raw:
        eng_key = normalizer._skill_key(eng_skill)
        eng_hard = normalizer.normalize_hard(eng_skill)
        eng_soft = normalizer.normalize_soft(eng_skill)
        matched = (
            eng_hard == canonical
            or eng_soft == canonical
            or eng_skill.strip() == canonical
            or (eng_key == req_key and req_key)
        )
        if not matched:
            continue
        if eng_key in normalizer.soft and normalizer.soft[eng_key] == canonical:
            saw_soft = True
        elif eng_key in normalizer.hard and normalizer.hard[eng_key] == canonical:
            if eng_skill.strip() == canonical or normalizer._skill_key(canonical) == eng_key:
                saw_exact = True
            else:
                saw_alias = True
        else:
            saw_exact = True

    if saw_exact:
        return "exact"
    if saw_alias:
        return "alias"
    if saw_soft:
        return "soft_alias"
    return "exact"


def _engineer_days_old(engineer: dict) -> int:
    _, days_old = _engineer_staleness_source(engineer)
    return days_old if days_old >= 0 else 0


def _calc_match_score(
    engineer: dict,
    hit_skills: list[str],
    alias_hits: list[str],
    soft_hits: list[str],
    case_max: float,
    eng_price: float,
) -> float:
    score = 1.0
    days = _engineer_days_old(engineer)
    if days > 14:
        score -= 0.2
    elif days > 7:
        score -= 0.1
    score += len(hit_skills) * 0.12 + len(alias_hits) * 0.08 + len(soft_hits) * 0.04
    gross = calc_gross_profit(case_max, eng_price)
    if gross >= 7:
        score += 0.1
    elif gross < 5:
        score -= 0.1
    parallel = _calc_parallel_score(engineer)
    if parallel >= 3.0:
        score -= 0.2
    elif parallel >= 2.0:
        score -= 0.1
    return round(max(0.0, min(2.0, score)), 3)


def _finalize_judge_result(
    result: dict[str, Any],
    engineer: dict,
    case_max: float,
    eng_price: float,
    exact_hits: list[str],
    alias_hits: list[str],
    soft_hits: list[str],
) -> dict[str, Any]:
    finalized = dict(result)
    finalized["score"] = _calc_match_score(
        engineer,
        exact_hits,
        alias_hits,
        soft_hits,
        case_max,
        eng_price,
    )
    return finalized


def _engineer_age(engineer: dict) -> int | None:
    raw = engineer.get("年齢")
    if raw is None:
        memo = engineer.get("備考（LINEメモ）") or engineer.get("名前") or ""
        match = re.search(r"(\d{2})歳", str(memo))
        if match:
            raw = match.group(1)
    if raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _evaluate_must_not(case_json: dict, engineer: dict) -> tuple[str | None, list[str]]:
    """否定条件チェック。verdict_override が NG のとき即除外。"""
    must_not = case_json.get("must_not") or []
    reasons: list[str] = []

    if "外国籍不可" in must_not:
        nationality = str(engineer.get("国籍") or "").strip()
        if nationality and nationality != "日本":
            return "NG", [f"案件条件: 外国籍不可（国籍={nationality}）"]

    age_max = case_json.get("age_max")
    if "年齢制限" in must_not or age_max is not None:
        engineer_age = _engineer_age(engineer)
        if age_max is not None and engineer_age is not None and engineer_age > int(age_max):
            return "NG", [f"年齢制限超過: {engineer_age}歳 > {age_max}歳"]

    if "出社必須" in must_not:
        if case_json.get("remote_ok") in ("full",):
            reasons.append("案件は出社必須（リモート不可）")
        else:
            reasons.append("案件は出社必須")

    return None, reasons


def judge_with_meta(
    case_json: dict,
    engineer: dict,
    normalizer: SkillNormalizer,
    assignee: str | None = None,
) -> dict[str, Any]:
    reasons: list[str] = []

    must_not_verdict, must_not_reasons = _evaluate_must_not(case_json, engineer)
    if must_not_verdict == "NG":
        return {
            "verdict": "NG",
            "reasons": must_not_reasons,
            "process_requirements": [],
        }
    reasons.extend(must_not_reasons)

    if case_json.get("quality_flag") == "NEEDS_REVIEW":
        reasons.append("構造化品質不足: NEEDS_REVIEW")

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

    required_raw = _without_soft_skills(case_json.get("required_skills") or [])
    required_skills, competencies = _partition_required_skills(required_raw)
    if competencies:
        logger.info("competency requirements excluded from skill match: %s", competencies)

    floor = _gross_threshold(assignee or case_json.get("担当者"))
    if not meets_profit_floor(case_max, eng_price, floor):
        gross = calc_gross_profit(case_max, eng_price)
        return _finalize_judge_result(
            {
                "verdict": "NG",
                "reasons": [f"粗利不足: {gross}万円 < 最低粗利{int(floor)}万円"],
                "process_requirements": competencies,
            },
            engineer,
            case_max,
            eng_price,
            [],
            [],
            [],
        )

    required_skills = _dedupe_required_by_parent(required_skills, normalizer)

    eng_skills_raw = [str(skill) for skill in (engineer.get("正規化スキル") or engineer.get("スキル") or [])]
    eng_skills = set()
    for skill in eng_skills_raw:
        normalized = normalizer.resolve_canonical(skill) or normalizer.normalize_hard(skill)
        eng_skills.add(normalized if normalized else skill)

    miss_skills: list[str] = []
    unknown_skills: list[str] = []
    soft_alias_only: list[str] = []
    exact_hits: list[str] = []
    alias_hits: list[str] = []
    soft_hits: list[str] = []
    tier1_hits = tier2_hits = tier3_hits = 0
    exact_count = alias_count = soft_alias_count = 0

    for skill in required_skills:
        hard = normalizer.normalize_hard(skill)
        soft_canon = normalizer.normalize_soft(skill) if hard is None else None
        tier_canon = None
        if hard is None and soft_canon is None:
            key = normalizer._skill_key(skill)
            for canon in normalizer.skill_tiers:
                if canon.lower() == key:
                    tier_canon = canon
                    break
        canonical = hard or soft_canon or tier_canon

        if canonical is None:
            unknown_skills.append(skill)
            continue
        if not _engineer_has_canonical(canonical, eng_skills, normalizer.parent_skills):
            miss_skills.append(skill)
            continue
        hit_kind = _classify_required_hit(skill, canonical, eng_skills_raw, normalizer)
        if hit_kind == "exact":
            exact_count += 1
            exact_hits.append(skill)
        elif hit_kind == "alias":
            alias_count += 1
            alias_hits.append(skill)
        else:
            soft_alias_count += 1
            soft_hits.append(skill)
            soft_alias_only.append(skill)
        tier = normalizer.skill_tier(canonical)
        if tier == 3:
            tier3_hits += 1
        elif tier == 2:
            tier2_hits += 1
        else:
            tier1_hits += 1

    score_components = {
        "exact_count": exact_count,
        "alias_count": alias_count,
        "soft_alias_count": soft_alias_count,
        "tier3_count": tier3_hits,
    }

    if miss_skills:
        return _finalize_judge_result(
            {
                "verdict": "NG",
                "reasons": [f"必須スキル不足: {miss_skills}"],
                "process_requirements": competencies,
                "score_components": score_components,
            },
            engineer,
            case_max,
            eng_price,
            exact_hits,
            alias_hits,
            soft_hits,
        )

    if soft_alias_only and exact_count == 0 and alias_count == 0:
        try:
            from common.failure_collector import collect_failure

            collect_failure(
                "partial_only",
                {"soft_alias_only": soft_alias_only, "engineer_id": engineer.get("id")},
                f"ソフトエイリアスのみ一致: {soft_alias_only}",
            )
        except Exception:
            pass
        return _finalize_judge_result(
            {
                "verdict": "PARTIAL_MATCH",
                "reasons": [f"ソフトエイリアスのみ一致: {soft_alias_only}"],
                "process_requirements": competencies,
                "score_components": score_components,
            },
            engineer,
            case_max,
            eng_price,
            exact_hits,
            alias_hits,
            soft_hits,
        )

    if tier3_hits > 0 and tier1_hits == 0 and tier2_hits == 0:
        return _finalize_judge_result(
            {
                "verdict": "REVIEW",
                "reasons": ["Tier3抽象スキルのみ一致（Tier1/2不足）"],
                "process_requirements": competencies,
                "score_components": score_components,
            },
            engineer,
            case_max,
            eng_price,
            exact_hits,
            alias_hits,
            soft_hits,
        )

    unknown_with_evidence: list[str] = []
    unknown_no_evidence: list[str] = []
    for skill in unknown_skills:
        if _fuzzy_match(skill, eng_skills_raw, strict_keys=normalizer.strict_keys):
            unknown_with_evidence.append(skill)
        else:
            unknown_no_evidence.append(skill)
    if unknown_with_evidence:
        logger.info("unknown skills with engineer DB evidence: %s", unknown_with_evidence)

    p_score = _calc_parallel_score(engineer)
    if p_score >= 5.0:
        return _finalize_judge_result(
            {
                "verdict": "NG",
                "reasons": [f"並行過多: スコア{p_score:.1f}（上限5.0）"],
                "process_requirements": competencies,
                "score_components": score_components,
            },
            engineer,
            case_max,
            eng_price,
            exact_hits,
            alias_hits,
            soft_hits,
        )

    if not is_engineer_fresh(engineer):
        source_value, days_old = _engineer_staleness_source(engineer)
        if source_value and days_old >= 0:
            reasons.append(f"エンジニア情報古い（{days_old}日前更新）")
        else:
            reasons.append("エンジニア情報古い（最終更新日不明）")

    ambiguous_skills = _without_soft_skills(case_json.get("ambiguous_skills") or [])
    if ambiguous_skills:
        reasons.append(f"曖昧スキルあり: {ambiguous_skills}")

    conf = float(case_json.get("extraction_confidence", 1.0) or 0.0)
    if conf < 0.3:
        reasons.append(f"構造化精度低: {conf:.2f}")

    unknown_ratio = len(unknown_no_evidence) / max(len(required_raw), 1)
    if unknown_ratio <= UNKNOWN_MATCH_RATIO_THRESHOLD:
        if unknown_no_evidence:
            reasons.append(f"語彙外スキル({len(unknown_no_evidence)}件)あるがMATCH判定")
        if not reasons:
            return _finalize_judge_result(
                {
                    "verdict": "MATCH",
                    "reasons": [],
                    "process_requirements": competencies,
                    "score_components": score_components,
                },
                engineer,
                case_max,
                eng_price,
                exact_hits,
                alias_hits,
                soft_hits,
            )
        non_critical = all(
            reason.startswith("語彙外")
            or reason.startswith("エンジニア情報古い")
            or reason.startswith("案件単価推定")
            or reason.startswith("エンジニア単価推定")
            for reason in reasons
        )
        if non_critical:
            return _finalize_judge_result(
                {
                    "verdict": "MATCH",
                    "reasons": reasons,
                    "process_requirements": competencies,
                    "score_components": score_components,
                },
                engineer,
                case_max,
                eng_price,
                exact_hits,
                alias_hits,
                soft_hits,
            )
        non_ambig = [reason for reason in reasons if not reason.startswith("曖昧スキルあり")]
        if not non_ambig:
            return _finalize_judge_result(
                {
                    "verdict": "NG",
                    "reasons": ["曖昧スキルのみ: 判定不可"],
                    "process_requirements": competencies,
                },
                engineer,
                case_max,
                eng_price,
                exact_hits,
                alias_hits,
                soft_hits,
            )
        return _finalize_judge_result(
            {
                "verdict": "REVIEW",
                "reasons": reasons,
                "process_requirements": competencies,
                "score_components": score_components,
            },
            engineer,
            case_max,
            eng_price,
            exact_hits,
            alias_hits,
            soft_hits,
        )

    if unknown_no_evidence:
        reasons.append(f"語彙外必須スキル要確認: {', '.join(unknown_no_evidence)}")

    if reasons:
        non_ambig = [reason for reason in reasons if not reason.startswith("曖昧スキルあり")]
        if not non_ambig:
            return _finalize_judge_result(
                {
                    "verdict": "NG",
                    "reasons": ["曖昧スキルのみ: 判定不可"],
                    "process_requirements": competencies,
                },
                engineer,
                case_max,
                eng_price,
                exact_hits,
                alias_hits,
                soft_hits,
            )
        return _finalize_judge_result(
            {
                "verdict": "REVIEW",
                "reasons": reasons,
                "process_requirements": competencies,
                "score_components": score_components,
            },
            engineer,
            case_max,
            eng_price,
            exact_hits,
            alias_hits,
            soft_hits,
        )
    return _finalize_judge_result(
        {
            "verdict": "MATCH",
            "reasons": [],
            "process_requirements": competencies,
            "score_components": score_components,
        },
        engineer,
        case_max,
        eng_price,
        exact_hits,
        alias_hits,
        soft_hits,
    )


def judge(
    case_json: dict,
    engineer: dict,
    normalizer: SkillNormalizer,
    assignee: str | None = None,
) -> tuple[str, list[str]]:
    result = judge_with_meta(case_json, engineer, normalizer, assignee)
    return result["verdict"], result["reasons"]


def optional_skill_bonus_ok(case_json: dict, engineer: dict, normalizer: SkillNormalizer) -> bool:
    optional_raw = case_json.get("optional_skills") or []
    if not optional_raw:
        return False
    eng_skills: set[str] = set()
    for skill in engineer.get("スキル") or []:
        hard = normalizer.normalize_hard(skill)
        if hard:
            eng_skills.add(hard)
        soft = normalizer.normalize_soft(skill)
        if soft:
            eng_skills.add(soft)
    normalized = [normalizer.normalize_hard(skill) or normalizer.normalize_soft(skill) for skill in optional_raw]
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


def _extract_result_wait_days(remark: str, *, today: date | None = None) -> int | None:
    """備考テキストから結果待ち日数を推定"""
    reference = today or date.today()
    match = re.search(r"結果待ち.*?(\d{1,2})[/月](\d{1,2})", remark)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        interview_date = reference.replace(month=month, day=day)
        if interview_date > reference:
            interview_date = interview_date.replace(year=reference.year - 1)
        return max(0, (reference - interview_date).days)

    if "結果待ち" in remark:
        return None

    return None


def _result_wait_score(days: int | None) -> float:
    if days is None:
        return 2.0
    return _score_result_waiting(days)


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
        days = _extract_result_wait_days(memo, today=reference)
        score += _result_wait_score(days)
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


def partition_fresh_engineers(
    engineers: list[dict],
    log: logging.Logger | None = None,
) -> tuple[list[dict], int]:
    """鮮度OKの人材リストと除外件数を返す。"""
    active_logger = log or logger
    fresh: list[dict] = []
    excluded = 0
    for engineer in engineers:
        if is_engineer_fresh(engineer):
            fresh.append(engineer)
            continue
        excluded += 1
        name = engineer.get("名前", engineer.get("id", ""))
        source_value, days_old = _engineer_staleness_source(engineer)
        if not source_value or days_old < 0:
            active_logger.info("stale: %s (最終更新日不明)", name)
        else:
            active_logger.info("stale: %s (%d日経過)", name, days_old)
    return fresh, excluded


def filter_fresh_engineers(
    engineers: list[dict],
    log: logging.Logger | None = None,
) -> list[dict]:
    """21日超の人材をマッチング対象から除外し、除外分をログに記録する。"""
    fresh, _ = partition_fresh_engineers(engineers, log)
    return fresh


def unit_price_review_reason(value: Any) -> str | None:
    """単価が無効な場合に理由ラベルを返す。有効なら None。"""
    if value is None:
        return "単価未設定"
    if isinstance(value, str):
        if not value.strip():
            return "単価未設定"
        try:
            parsed = float(value.strip())
        except ValueError:
            return "単価未設定"
    else:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return "単価未設定"
    if parsed < 0:
        return "単価が負数"
    if parsed == 0:
        return "単価0円"
    return None


MEMO_APPEND_MAX_LEN = 1800


def build_unit_price_review_memo(existing_memo: str, reason: str, review_date: date | None = None) -> str:
    """備考末尾に単価REVIEW行を追記する。既にタグがあれば変更しない。"""
    memo = existing_memo or ""
    if UNIT_PRICE_REVIEW_TAG in memo:
        return memo
    today = (review_date or date.today()).isoformat()
    suffix = f"{UNIT_PRICE_REVIEW_TAG}{reason} {today}"
    if memo:
        return f"{memo}\n{suffix}"
    return suffix


def engineer_unit_price_man(engineer: dict) -> float | None:
    """エンジニア単価を万円単位で返す。単価(円)・単価（万円）の両方に対応。"""
    man_value = engineer.get("単価（万円）")
    if man_value is not None:
        try:
            return float(man_value)
        except (TypeError, ValueError):
            return None
    yen_value = engineer.get("単価")
    if yen_value is not None:
        try:
            return float(yen_value) / 10000
        except (TypeError, ValueError):
            return None
    return None


def _is_proposal_target(engineer: dict) -> bool:
    return bool(engineer.get("提案対象フラグ"))


def find_unit_price_review_targets(engineers: list[dict]) -> list[tuple[dict, str]]:
    """提案対象かつ単価無効のエンジニアと理由ラベルのリスト。"""
    targets: list[tuple[dict, str]] = []
    for engineer in engineers:
        if not _is_proposal_target(engineer):
            continue
        reason = unit_price_review_reason(engineer_unit_price_man(engineer))
        if reason:
            targets.append((engineer, reason))
    return targets


def exclude_unit_price_review_targets(
    engineers: list[dict],
    log: logging.Logger | None = None,
) -> list[dict]:
    """単価REVIEW対象をマッチング候補から除外する。"""
    active_logger = log or logger
    excluded_ids = {engineer["id"] for engineer, _ in find_unit_price_review_targets(engineers)}
    if not excluded_ids:
        return engineers
    kept: list[dict] = []
    for engineer in engineers:
        if engineer.get("id") in excluded_ids:
            name = engineer.get("名前", engineer.get("id", ""))
            reason = unit_price_review_reason(engineer_unit_price_man(engineer)) or ""
            active_logger.info("[REVIEW除外] %s — 理由: %s", name, reason)
            continue
        kept.append(engineer)
    return kept


class UnitPriceReviewUpdater(Protocol):
    def update_engineer_unit_price_review(self, page_id: str, memo_text: str) -> bool: ...


def load_engineers(notion_client: Any | None = None) -> list[dict]:
    """Notionから提案対象エンジニアを読み取る（更新なし）。"""
    if notion_client is None:
        from notion_client import NotionClient

        notion_client = NotionClient()
    return notion_client.get_proposal_target_engineers()


def review_invalid_unit_price(
    engineers: list[dict],
    *,
    dry_run: bool = True,
    updater: UnitPriceReviewUpdater | None = None,
    log: logging.Logger | None = None,
    review_date: date | None = None,
) -> dict[str, Any]:
    """
    単価無効の提案対象エンジニアをREVIEW処理する。
    dry_run=True のときはログ出力のみ。False のとき Notion を更新する。
    """
    active_logger = log or logger
    targets = find_unit_price_review_targets(engineers)
    update_success = 0
    update_failed = 0

    for engineer, reason in targets:
        name = engineer.get("名前", engineer.get("id", ""))
        active_logger.info("[REVIEW] %s — 理由: %s", name, reason)
        if dry_run:
            continue
        if updater is None:
            raise ValueError("updater is required when dry_run=False")
        existing_memo = engineer.get(ENGINEER_MEMO_FIELD) or ""
        if len(existing_memo) > MEMO_APPEND_MAX_LEN:
            active_logger.warning(
                "[WARN] %s — 備考が長すぎるため追記スキップ（%d文字）",
                name,
                len(existing_memo),
            )
            update_failed += 1
            continue
        memo = build_unit_price_review_memo(
            existing_memo,
            reason,
            review_date=review_date,
        )
        if updater.update_engineer_unit_price_review(engineer["id"], memo):
            update_success += 1
        else:
            update_failed += 1

    summary = {
        "target_count": len(targets),
        "update_success": update_success,
        "update_failed": update_failed,
        "targets": [{"engineer": eng, "reason": reason} for eng, reason in targets],
    }
    active_logger.info(
        "REVIEW対象%d件 / 更新成功%d件 / 更新失敗%d件",
        summary["target_count"],
        summary["update_success"],
        summary["update_failed"],
    )
    return summary


def run_audit_unit_price(*, exec_mode: bool = False) -> int:
    """audit-unit-price サブコマンドのエントリポイント。"""
    from notion_client import NotionClient

    notion = NotionClient()
    engineers = load_engineers(notion)
    summary = review_invalid_unit_price(
        engineers,
        dry_run=not exec_mode,
        updater=notion if exec_mode else None,
    )
    if exec_mode and summary.get("update_failed", 0) > 0:
        return 1
    return 0


def _parse_cli_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="matching_v3 matcher utilities")
    subparsers = parser.add_subparsers(dest="command")
    audit = subparsers.add_parser("audit-unit-price", help="単価無効エンジニアのREVIEW監査")
    audit.add_argument("--exec", action="store_true", help="Notionを更新する（省略時はドライラン）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_cli_args(argv)
    if args.command == "audit-unit-price":
        return run_audit_unit_price(exec_mode=args.exec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
