"""Engineer-side rate extractor — wraps core logic with engineer-specific patterns."""
from __future__ import annotations

import re
import sys
import unicodedata
from dataclasses import dataclass

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engineer_extractor.engineer_text_parser import ParsedEngineerText


@dataclass
class RateResult:
    rate: int | None = None
    rate_min: int | None = None
    rate_max: int | None = None
    rate_text_raw: str | None = None
    negotiable: bool = False
    skill_dependent: bool = False
    confidence: float = 0.0
    source: str = "none"  # "labeled" | "subject_bracket" | "body"


def _normalize(text: str) -> str:
    n = unicodedata.normalize("NFKC", text)
    return re.sub(r"(\d),(\d)", r"\1\2", n)


def _parse_man_value(s: str) -> int | None:
    try:
        v = float(s)
    except (ValueError, TypeError):
        return None
    if v < 1 or v > 200:
        return None
    return int(v)


# Patterns ordered by specificity
_RANGE_RE = re.compile(r"(\d{2,3})\s*万?円?\s*[〜～\-~]\s*(\d{2,3})\s*万")
_UPPER_ONLY_RE = re.compile(r"[〜～~]\s*(\d{2,3})\s*万")
_LABEL_RE = re.compile(r"(?:単価|希望単価|月額)\s*[:：]?\s*(\d{2,3})\s*万")
_BRACKET_RATE_RE = re.compile(r"【[^】]*?(\d{2,3})万[^】]*?】")
_PLAIN_MAN_RE = re.compile(r"(?<!\d)(\d{2,3})\s*万(?:円)?(?!\d)")
_NEGOTIABLE_RE = re.compile(r"応相談|要相談|ご相談|交渉可|negotiable", re.IGNORECASE)
_SKILL_DEPENDENT_RE = re.compile(r"スキル見合|経験見合|ご経験見合|スキル次第|スキルにより")


def _extract_from_text(text: str) -> RateResult | None:
    normalized = _normalize(text)

    negotiable = bool(_NEGOTIABLE_RE.search(normalized))
    skill_dep = bool(_SKILL_DEPENDENT_RE.search(normalized))

    # range match
    m = _RANGE_RE.search(normalized)
    if m:
        lo = _parse_man_value(m.group(1))
        hi = _parse_man_value(m.group(2))
        if lo and hi:
            if lo > hi:
                lo, hi = hi, lo
            return RateResult(
                rate=hi,
                rate_min=lo,
                rate_max=hi,
                rate_text_raw=m.group(0).strip(),
                negotiable=negotiable,
                skill_dependent=skill_dep,
                confidence=0.90,
            )

    # upper-only
    m = _UPPER_ONLY_RE.search(normalized)
    if m:
        v = _parse_man_value(m.group(1))
        if v:
            return RateResult(
                rate=v,
                rate_max=v,
                rate_text_raw=m.group(0).strip(),
                negotiable=negotiable,
                skill_dependent=skill_dep,
                confidence=0.85,
            )

    # explicit label
    m = _LABEL_RE.search(normalized)
    if m:
        v = _parse_man_value(m.group(1))
        if v:
            return RateResult(
                rate=v,
                rate_max=v,
                rate_text_raw=m.group(0).strip(),
                negotiable=negotiable,
                skill_dependent=skill_dep,
                confidence=0.88,
            )

    # plain XxX万 (loose)
    m = _PLAIN_MAN_RE.search(normalized)
    if m:
        v = _parse_man_value(m.group(1))
        if v:
            return RateResult(
                rate=v,
                rate_max=v,
                rate_text_raw=m.group(0).strip(),
                negotiable=negotiable,
                skill_dependent=skill_dep,
                confidence=0.70,
            )

    if skill_dep:
        return RateResult(skill_dependent=True, confidence=0.80)

    return None


def extract_rate(parsed: ParsedEngineerText) -> RateResult:
    # Layer 1: labeled_fields
    for key in ("単価", "希望単価"):
        if key in parsed.labeled_fields:
            r = _extract_from_text(parsed.labeled_fields[key])
            if r:
                r.source = "labeled"
                # labeled source warrants higher confidence floor
                r.confidence = max(r.confidence, 0.85)
                return r

    # Layer 2: subject bracket
    if parsed.subject:
        m = _BRACKET_RATE_RE.search(_normalize(parsed.subject))
        if m:
            v = _parse_man_value(m.group(1))
            if v:
                negotiable = bool(_NEGOTIABLE_RE.search(m.group(0)))
                return RateResult(
                    rate=v,
                    rate_max=v,
                    rate_text_raw=m.group(0).strip(),
                    negotiable=negotiable,
                    confidence=0.88,
                    source="subject_bracket",
                )

    # Layer 3: full body
    r = _extract_from_text(parsed.body or parsed.full_text)
    if r:
        r.source = "body"
        return r

    return RateResult(confidence=0.0, source="none")
