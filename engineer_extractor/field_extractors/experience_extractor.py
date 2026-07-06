"""Experience extractor — extracts years of experience from engineer text."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engineer_extractor.engineer_text_parser import ParsedEngineerText


@dataclass
class ExperienceResult:
    years: float | None = None
    confidence: float = 0.0
    source: str = "none"
    evidence: str | None = None


_EXP_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    # e.g. "経験年数：10年", "【経験】15年"
    (re.compile(r"(?:経験年数|開発歴|業界歴|SE歴|IT歴|エンジニア歴)[:：は]?\s*(\d+(?:\.\d+)?)\s*年"), 0.92),
    # "iOS開発11年", "Java開発8年"
    (re.compile(r"[^\s。、\n]{2,15}開発\s*(\d+(?:\.\d+)?)\s*年"), 0.85),
    # "SE経験10年以上", "エンジニア経験5年"
    (re.compile(r"[^\s。、\n]{1,10}経験\s*(\d+(?:\.\d+)?)\s*年"), 0.82),
    # "4.5年" or "11年" when surrounded by context words
    (re.compile(r"(?:約|経験|歴)?\s*(\d+(?:\.\d+)?)\s*年(?:以上|超|程度|前後|ほど)?"), 0.65),
]


def _parse_years(raw: str) -> float | None:
    try:
        v = float(raw)
    except (ValueError, TypeError):
        return None
    if v < 0.5 or v > 50:
        return None
    return v


def extract_experience(parsed: ParsedEngineerText) -> ExperienceResult:
    # labeled_fields priority
    if "経験" in parsed.labeled_fields:
        raw = parsed.labeled_fields["経験"]
        m = re.search(r"(\d+(?:\.\d+)?)\s*年", raw)
        if m:
            y = _parse_years(m.group(1))
            if y:
                return ExperienceResult(years=y, confidence=0.92, source="labeled", evidence=raw)

    # scan subject then body
    for text, src in [
        (parsed.subject or "", "subject"),
        (parsed.body or parsed.full_text, "body"),
    ]:
        if not text:
            continue
        for pat, conf in _EXP_PATTERNS:
            m = pat.search(text)
            if m:
                y = _parse_years(m.group(1))
                if y:
                    return ExperienceResult(
                        years=y, confidence=conf, source=src, evidence=m.group(0).strip()
                    )

    return ExperienceResult(confidence=0.0, source="none")
