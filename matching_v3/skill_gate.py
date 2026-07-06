"""マッチング品質ゲート: OOV fail-closed / 低品質除外 / denylist分類。"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DENYLIST_PATH = BASE_DIR / "denylist.json"
PROCESS_SKILLS_PATH = BASE_DIR.parent / "config" / "process_skills.json"
MALFORMED_PATTERN = re.compile(r"[】【\[\]{}]")
from skill_pre_normalize import pre_normalize_skill_text, pre_normalize_skill_tokens

logger = logging.getLogger(__name__)

_TECH_SKILL_NAMES = (
    "Java",
    "Python",
    "PHP",
    "C#",
    "AWS",
    "Azure",
    "GCP",
    "React",
    "Vue",
    "Angular",
    "Docker",
    "Kubernetes",
    "Linux",
    "Oracle",
    "MySQL",
    "PostgreSQL",
    "SQL",
    "Spring",
    "TypeScript",
    "JavaScript",
    r"Node\.js",
    "Go",
    "Ruby",
    "Kotlin",
    "Swift",
    "Terraform",
    "Jenkins",
    "Salesforce",
    "COBOL",
    "VBA",
    "Excel",
    "Word",
    "PowerShell",
    "Shell",
    "HTML",
    "CSS",
)
_TECH_NAMES_PATTERN = "|".join(_TECH_SKILL_NAMES)
_P1_CAT1_RE = re.compile(rf"^({_TECH_NAMES_PATTERN})(経験|実績)$")
_P1_CAT2_RE = re.compile(
    rf"^({_TECH_NAMES_PATTERN})(?:開発|設計|構築|運用|保守|導入|移行)+経験$"
)
_P1_CAT3_RE = re.compile(r"^(要件定義|基本設計|詳細設計|製造|テスト|運用|保守)経験$")
_P1_LOW_TRUST_SUFFIXES = ("知識", "スキル", "対応可", "案件", "業務")

# Categories used for classify_skill() priority ordering (legacy + new)
CATEGORY_ORDER = (
    "task_words",
    "soft_traits",
    "licenses",
    "noise",
    "punctuation",
    "email_boilerplate",
    "generic_business",
    "stopwords",
    "format_artifacts",
)

# Regex for email signature / business header patterns
_EMAIL_SIG_RE = re.compile(
    r"(?:株式会社|合同会社|有限会社|御中|殿|TEL[:：]|FAX[:：]|〒|E[-－]?mail[:：]|@[a-zA-Z0-9]+\.[a-zA-Z]{2,})"
)
# Matches alphanumeric or typical CJK word characters
_ALPHANUM_OR_CJK = re.compile(r"[a-zA-Z0-9぀-ヿ一-鿿ｦ-ﾟ]")


@lru_cache(maxsize=1)
def load_denylist() -> dict[str, tuple[str, ...]]:
    if not DENYLIST_PATH.exists():
        return {key: tuple() for key in CATEGORY_ORDER}
    data = json.loads(DENYLIST_PATH.read_text(encoding="utf-8"))
    # Support both flat list (legacy) and categorical dict
    if isinstance(data, list):
        return {"noise": tuple(data)}
    return {key: tuple(values) for key, values in data.items() if isinstance(values, list)}


@lru_cache(maxsize=1)
def denylist_flat() -> frozenset[str]:
    flat: set[str] = set()
    for values in load_denylist().values():
        for value in values:
            flat.add(value.strip().lower())
    return frozenset(flat)


@lru_cache(maxsize=1)
def load_process_skills() -> frozenset[str]:
    if not PROCESS_SKILLS_PATH.exists():
        return frozenset()
    items = json.loads(PROCESS_SKILLS_PATH.read_text(encoding="utf-8"))
    return frozenset(str(skill).strip() for skill in items if str(skill).strip())


def normalize_skill_text(raw_skill: str) -> str:
    """P1: 高信頼パターンのみスキル表記を正規化する。"""
    text = pre_normalize_skill_text(raw_skill)
    text = unicodedata.normalize("NFKC", text)
    if not text:
        return text
    for suffix in _P1_LOW_TRUST_SUFFIXES:
        if text.endswith(suffix):
            return text
    match = _P1_CAT3_RE.match(text)
    if match:
        return match.group(1)
    match = _P1_CAT2_RE.match(text)
    if match:
        return match.group(1)
    match = _P1_CAT1_RE.match(text)
    if match:
        return match.group(1)
    return text


def log_skill_text_normalization(raw_skill: str, normalized_skill: str) -> None:
    if normalized_skill != (raw_skill or "").strip():
        logger.info(
            "skill_p1_normalize raw=%s normalized=%s",
            raw_skill,
            normalized_skill,
        )


def is_process_skill_name(skill: str) -> bool:
    text = unicodedata.normalize("NFKC", (skill or "").strip())
    if not text:
        return False
    return text in load_process_skills()


def normalize_process_skills(skills: list[str], *, use_p1: bool = True) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        if not validate_skill_for_matching(skill)[0]:
            continue
        text = normalize_skill_text(skill) if use_p1 else str(skill).strip()
        if use_p1:
            log_skill_text_normalization(skill, text)
        if not is_process_skill_name(text):
            continue
        if text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _is_rule_deny(text: str) -> tuple[bool, str]:
    """ルールベースのdeny判定: 記号・署名パターン等。"""
    if not text:
        return False, ""
    # Rule 1: single non-alphanumeric character
    if len(text) == 1 and not text[0].isalnum():
        return True, "single_symbol"
    # Rule 2: contains no alphanumeric or CJK word characters (symbol/format only)
    if not _ALPHANUM_OR_CJK.search(text):
        return True, "symbol_only"
    # Rule 3: email signature / business header pattern
    if _EMAIL_SIG_RE.search(text):
        return True, "email_signature"
    return False, ""


def is_malformed_skill(skill: str) -> bool:
    return bool(MALFORMED_PATTERN.search(skill or ""))


def classify_skill(skill: str) -> str:
    text = (skill or "").strip()
    if not text:
        return "EMPTY"
    if is_malformed_skill(text):
        return "MALFORMED"
    lowered = text.lower()
    denylist = load_denylist()
    # Check CATEGORY_ORDER first, then any remaining categories
    all_categories = list(CATEGORY_ORDER) + [k for k in denylist if k not in CATEGORY_ORDER]
    for category in all_categories:
        for word in denylist.get(category, ()):
            if lowered == word.lower():
                return category.upper()
    return "TECH_SKILL"


def is_technical_skill(skill: str) -> bool:
    return classify_skill(skill) == "TECH_SKILL"


def validate_skill_for_matching(skill: str) -> tuple[bool, str]:
    text = (skill or "").strip()
    if not text:
        return False, "empty"
    if is_malformed_skill(text):
        return False, "malformed"
    rule_denied, rule_reason = _is_rule_deny(text)
    if rule_denied:
        return False, f"rule_deny:{rule_reason}"
    if text.lower() in denylist_flat():
        return False, "denylisted"
    return True, "ok"


def extract_raw_required_skills(
    case: dict[str, Any],
    case_json: dict[str, Any],
) -> list[str]:
    """マッチング前の必須スキル原文（denylist適用前）。"""
    notion_skills = case.get("必要スキル") or []
    if notion_skills:
        return [str(skill).strip() for skill in notion_skills if str(skill).strip()]

    struct_skills = case_json.get("required_skills") or []
    if struct_skills:
        return [str(skill).strip() for skill in struct_skills if str(skill).strip()]

    return []


def normalize_technical_skills(
    skills: list[str],
    normalizer: Any,
    *,
    use_p1: bool = True,
) -> list[str]:
    """辞書解決できた技術スキルのみ返す。運用保守サフィックスは2トークン化して両方を保持する。"""
    result: list[str] = []
    seen: set[str] = set()
    for skill in skills:
        if not validate_skill_for_matching(skill)[0]:
            continue
        if use_p1:
            # 2トークン化（運用保守split + 経験lookup-time strip）
            tokens = pre_normalize_skill_tokens(skill, lookup=normalizer.resolve_canonical)
        else:
            tokens = [str(skill).strip()]
        for raw_token in tokens:
            text = normalize_skill_text(raw_token) if use_p1 else raw_token
            if use_p1:
                log_skill_text_normalization(skill, text)
            if is_process_skill_name(text):
                continue
            if not is_technical_skill(text):
                continue
            canonical = normalizer.resolve_canonical(str(text)) or ""
            if canonical and canonical not in seen:
                seen.add(canonical)
                result.append(canonical)
    return result


def evaluate_matchability(
    case_json: dict[str, Any],
    extracted_required_skills: list[str],
    normalized_technical_skills: list[str],
    normalized_process_skills: list[str] | None = None,
) -> tuple[bool, str, str, str]:
    """
    Returns:
        (matchable, status, reason, ng_reason)
    """
    confidence = case_json.get("extraction_confidence")
    if confidence is not None:
        try:
            conf_value = float(confidence)
        except (TypeError, ValueError):
            conf_value = None
        else:
            if conf_value < 0.5:
                return (
                    False,
                    "UNMATCHABLE_LOW_QUALITY",
                    "構造化品質不足のためマッチング不可",
                    "LOW_EXTRACTION_CONFIDENCE",
                )

    process_skills = normalized_process_skills
    if process_skills is None and extracted_required_skills:
        process_skills = normalize_process_skills(extracted_required_skills)

    if extracted_required_skills and not normalized_technical_skills and not process_skills:
        return (
            False,
            "UNMATCHABLE_SKILL_OOV",
            "全必須スキルが辞書外のためマッチング不可",
            "ALL_REQUIRED_SKILLS_OOV",
        )

    return True, "", "", ""
