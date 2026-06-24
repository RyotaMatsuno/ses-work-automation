"""Notion案件DB保存用: structurer連携・スキル正規化・バリデーション。"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

SES_WORK = Path(__file__).resolve().parents[1]
MATCHING_V3 = SES_WORK / "matching_v3"
if str(SES_WORK) not in sys.path:
    sys.path.insert(0, str(SES_WORK))


from mail_pipeline.price_extractor import resolve_final_price
from mail_pipeline.skill_extractor import extract_skills

logger = logging.getLogger(__name__)

ALIASES_PATH = MATCHING_V3 / "skill_aliases.json"
BACKFILL_SOURCE_TAG = "[source=backfill]"

_SKILL_HINT_RE = re.compile(
    r"(?:java|python|react|vue|angular|aws|gcp|azure|spring|docker|kubernetes|"
    r"typescript|javascript|php|go\b|sql|oracle|mysql|infra|インフラ|pmo)",
    re.IGNORECASE,
)


def _get_normalizer():
    if str(MATCHING_V3) not in sys.path:
        sys.path.append(str(MATCHING_V3))
    from matcher import SkillNormalizer

    return SkillNormalizer(ALIASES_PATH)


def _extract_work_location(subject: str, body: str) -> str | None:
    for text in (body, subject):
        match = re.search(r"勤務地\s*[:：]\s*([^\n\r]+)", text)
        if match:
            return match.group(1).strip()[:200]
    return None


def canonicalize_skills_for_notion(skills: list[str]) -> list[str]:
    """skill_aliases.json で canonical 名に正規化（Notion multi_select 用）。"""
    normalizer = _get_normalizer()
    canonical: list[str] = []
    seen: set[str] = set()
    for raw in skills:
        if not raw or not str(raw).strip():
            continue
        for part in re.split(r"[/／、,]", str(raw)):
            part = part.strip()
            if not part:
                continue
            target = (
                normalizer.normalize_hard(part)
                or normalizer.normalize_soft(part)
                or normalizer.resolve_canonical(part)
                or part
            )
            if target and target not in seen:
                seen.add(target)
                canonical.append(target)
    return canonical


def enrich_from_email_rules(info: dict[str, Any], subject: str, raw_body: str) -> dict[str, Any]:
    """ルールベース抽出で info を補完する（LLM不使用）。"""
    rule_result = extract_skills(subject, raw_body)
    enriched = dict(info)

    def _merge_list(key: str, extra: list[str]) -> None:
        existing = list(enriched.get(key) or [])
        merged: list[str] = []
        seen: set[str] = set()
        for item in existing + extra:
            low = str(item).strip().lower()
            if low and low not in seen:
                seen.add(low)
                merged.append(str(item).strip())
        if merged:
            enriched[key] = merged

    _merge_list("required_skills", rule_result.get("required") or [])
    _merge_list("optional_skills", rule_result.get("optional") or [])

    if enriched.get("price") is None:
        enriched["price"] = resolve_final_price(None, subject, raw_body)

    if not enriched.get("location"):
        enriched["location"] = _extract_work_location(subject, raw_body)

    return enriched


def prepare_notion_project_fields(
    info: dict[str, Any],
    subject: str,
    raw_body: str,
) -> tuple[list[str], list[str], float | None, str | None]:
    """案件登録用の必須/尚可スキル・単価・勤務地を準備する。"""
    enriched = enrich_from_email_rules(info, subject, raw_body)
    rule_result = extract_skills(subject, raw_body)

    required_raw: list[str] = []
    optional_raw: list[str] = []
    for source in (
        enriched.get("required_skills") or [],
        rule_result.get("required") or [],
    ):
        required_raw.extend(str(s) for s in source)
    for source in (
        enriched.get("optional_skills") or [],
        enriched.get("preferred_skills") or [],
        rule_result.get("optional") or [],
    ):
        optional_raw.extend(str(s) for s in source)

    required = canonicalize_skills_for_notion(required_raw)
    optional = canonicalize_skills_for_notion(optional_raw)
    optional = [skill for skill in optional if skill not in required]

    price = enriched.get("price")
    if price is None:
        price = resolve_final_price(None, subject, raw_body)

    location = enriched.get("location") or _extract_work_location(subject, raw_body)

    return required, optional, price, location


def subject_has_skill_hint(subject: str, raw_body: str) -> bool:
    text = f"{subject}\n{raw_body[:500]}"
    return bool(_SKILL_HINT_RE.search(text))


def log_project_save_warnings(
    name: str,
    properties: dict[str, Any],
    subject: str,
    raw_body: str,
    *,
    log_fn=logger.warning,
) -> None:
    """案件登録時のデータ品質警告。"""
    req = properties.get("必要スキル", {}).get("multi_select") or []
    if not req and subject_has_skill_hint(subject, raw_body):
        log_fn("[WARN] 案件名/本文にスキル語があるが必要スキルが空: %s", name[:60])

    if properties.get("単価（万円）", {}).get("number") is None:
        log_fn("[WARN] 単価が空: %s", name[:60])

    detail = properties.get("案件詳細", {}).get("rich_text") or []
    if not detail or not any(item.get("text", {}).get("content", "").strip() for item in detail):
        log_fn("[WARN] 案件詳細が空: %s", name[:60])


def extract_skills_for_backfill(subject: str, body: str, extra_text: str = "") -> tuple[list[str], list[str]]:
    """バックフィル用: ルールベースでスキル抽出。"""
    combined_body = "\n".join(part for part in (body, extra_text) if part)
    info = enrich_from_email_rules({}, subject, combined_body)
    return prepare_notion_project_fields(info, subject, combined_body)[:2]


def backfill_note_append(existing: str) -> str:
    note = (existing or "").strip()
    if BACKFILL_SOURCE_TAG in note:
        return note
    if note:
        return f"{note}\n{BACKFILL_SOURCE_TAG}"
    return BACKFILL_SOURCE_TAG
