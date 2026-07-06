"""Demographics extractor — extracts age and gender from engineer text."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engineer_extractor.engineer_text_parser import ParsedEngineerText


@dataclass
class DemographicsResult:
    age: int | None = None
    gender: str | None = None  # "男性" | "女性"
    confidence: float = 0.0
    source: str = "none"
    evidence: str | None = None


_AGE_GENDER_PATTERNS: list[tuple[re.Pattern[str], str, float]] = [
    # "33歳/男性", "33歳 男性"
    (re.compile(r"(\d{2})\s*歳\s*[/／・,、]\s*(男性|女性)"), "age_gender", 0.92),
    # "40歳男性", "40歳女性"
    (re.compile(r"(\d{2})\s*歳\s*(男性|女性)"), "age_gender", 0.92),
    # "(32)男性", "（32）女性"
    (re.compile(r"[（(](\d{2})[）)]\s*(男性|女性)"), "age_gender", 0.85),
    # "男性（33）", "女性（40）"
    (re.compile(r"(男性|女性)\s*[（(](\d{2})[）)]"), "gender_age", 0.85),
    # "33歳" alone
    (re.compile(r"(\d{2})\s*歳"), "age_only", 0.70),
    # gender alone  "男性", "女性" in context
    (re.compile(r"(?:^|\s|。|、)(男性|女性)(?:\s|。|、|$)"), "gender_only", 0.65),
]


def _parse_age(raw: str) -> int | None:
    try:
        v = int(raw)
    except (ValueError, TypeError):
        return None
    if v < 18 or v > 75:
        return None
    return v


def extract_demographics(parsed: ParsedEngineerText) -> DemographicsResult:
    # labeled_fields: "名前" often includes age+gender e.g. "Y.S（33歳男性）"
    for key in ("名前", "年齢", "性別"):
        if key in parsed.labeled_fields:
            r = _scan_text(parsed.labeled_fields[key], "labeled")
            if r.age or r.gender:
                return r

    for text, src in [
        (parsed.subject or "", "subject"),
        (parsed.body or parsed.full_text, "body"),
    ]:
        if not text:
            continue
        r = _scan_text(text, src)
        if r.age or r.gender:
            return r

    return DemographicsResult(confidence=0.0, source="none")


def _scan_text(text: str, source: str) -> DemographicsResult:
    for pat, kind, conf in _AGE_GENDER_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        if kind == "age_gender":
            age = _parse_age(m.group(1))
            gender = m.group(2)
            return DemographicsResult(age=age, gender=gender, confidence=conf,
                                      source=source, evidence=m.group(0).strip())
        if kind == "gender_age":
            gender = m.group(1)
            age = _parse_age(m.group(2))
            return DemographicsResult(age=age, gender=gender, confidence=conf,
                                      source=source, evidence=m.group(0).strip())
        if kind == "age_only":
            age = _parse_age(m.group(1))
            if age:
                return DemographicsResult(age=age, confidence=conf,
                                          source=source, evidence=m.group(0).strip())
        if kind == "gender_only":
            gender = m.group(1)
            return DemographicsResult(gender=gender, confidence=conf,
                                      source=source, evidence=m.group(0).strip())

    return DemographicsResult(confidence=0.0, source=source)
