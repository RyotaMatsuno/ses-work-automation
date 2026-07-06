"""Skills extractor — 4-layer extraction from engineer text."""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engineer_extractor.engineer_text_parser import ParsedEngineerText

_DICT_PATH = Path(__file__).parent.parent / "skill_dictionary.json"

with _DICT_PATH.open(encoding="utf-8") as _f:
    _SKILL_DICT = json.load(_f)

# flat list of canonical skill names (excluding aliases section)
_ALL_SKILLS: list[str] = []
for _cat, _items in _SKILL_DICT.items():
    if _cat != "aliases" and isinstance(_items, list):
        _ALL_SKILLS.extend(_items)

_ALIASES: dict[str, str] = _SKILL_DICT.get("aliases", {})

# compiled patterns for dictionary matching (case-insensitive)
_SKILL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (skill, re.compile(r"(?<![A-Za-z0-9._\-])" + re.escape(skill) + r"(?![A-Za-z0-9._\-])", re.IGNORECASE))
    for skill in _ALL_SKILLS
]

# compiled alias patterns
_ALIAS_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (alias, canonical, re.compile(r"(?<![A-Za-z0-9._\-])" + re.escape(alias) + r"(?![A-Za-z0-9._\-])"))
    for alias, canonical in _ALIASES.items()
]

_DELIMITERS = re.compile(r"[,、/／|・\n]+")
_BRACKET_CONTENT = re.compile(r"【([^】]+)】")


@dataclass
class SkillResult:
    skills: list[str] = field(default_factory=list)
    raw_skills: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source: str = "none"  # "labeled" | "subject" | "dictionary" | "heuristic"


def _normalize_skill(token: str) -> str | None:
    token = token.strip()
    if not token:
        return None
    # check aliases first
    for alias, canonical, pat in _ALIAS_PATTERNS:
        if pat.fullmatch(token):
            return canonical
    # check dictionary (case-insensitive match)
    token_lower = token.lower()
    for skill in _ALL_SKILLS:
        if skill.lower() == token_lower:
            return skill
    return None


def _split_skills(text: str) -> list[str]:
    parts = _DELIMITERS.split(text)
    return [p.strip() for p in parts if p.strip()]


def extract_skills(parsed: ParsedEngineerText) -> SkillResult:
    seen: set[str] = set()
    raw_seen: set[str] = set()

    def add_skills(raw_list: list[str], result_skills: list[str], result_raw: list[str]) -> None:
        for raw in raw_list:
            norm = _normalize_skill(raw)
            if norm and norm not in seen:
                seen.add(norm)
                result_skills.append(norm)
            if raw and raw not in raw_seen:
                raw_seen.add(raw)
                result_raw.append(raw)

    skills: list[str] = []
    raw_skills: list[str] = []
    source = "none"

    # Layer 1: labeled_fields["スキル"] or similar
    for key in ("スキル", "資格"):
        if key in parsed.labeled_fields:
            tokens = _split_skills(parsed.labeled_fields[key])
            add_skills(tokens, skills, raw_skills)
            if skills:
                source = "labeled"
            break

    # Layer 2: subject bracket extraction
    if parsed.subject:
        for m in _BRACKET_CONTENT.finditer(parsed.subject):
            bracket_text = m.group(1)
            # Heuristic: skill bracket has multiple tokens or known skills
            tokens = _split_skills(bracket_text)
            if len(tokens) > 1 or any(_normalize_skill(t) for t in tokens):
                add_skills(tokens, skills, raw_skills)
                if not source or source == "none":
                    source = "subject"

    # Layer 3: dictionary matching across full_text
    text = parsed.full_text
    dict_found: list[str] = []
    for canonical, pat in _SKILL_PATTERNS:
        if canonical not in seen and pat.search(text):
            dict_found.append(canonical)
    add_skills(dict_found, skills, raw_skills)
    if dict_found and source == "none":
        source = "dictionary"

    if not skills:
        return SkillResult(confidence=0.0, source="none")

    # confidence: labeled=0.95, subject=0.85, dictionary=0.70
    conf_map = {"labeled": 0.95, "subject": 0.85, "dictionary": 0.70, "heuristic": 0.50}
    confidence = conf_map.get(source, 0.5)

    return SkillResult(
        skills=skills,
        raw_skills=raw_skills,
        confidence=confidence,
        source=source,
    )
