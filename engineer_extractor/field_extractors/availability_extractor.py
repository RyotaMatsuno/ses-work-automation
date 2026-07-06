"""Availability extractor — extracts start date from engineer text."""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from engineer_extractor.engineer_text_parser import ParsedEngineerText

_TODAY = date.today()


@dataclass
class AvailabilityResult:
    start_date: str | None = None  # ISO 8601 YYYY-MM-DD
    is_immediate: bool = False
    inferred_year: bool = False
    confidence: float = 0.0
    source: str = "none"
    evidence: str | None = None


_ISO_DATE_RE = re.compile(r"(\d{4})[/\-年](\d{1,2})[/\-月](\d{1,2})")
_MONTH_ONLY_RE = re.compile(r"(\d{1,2})月(?:\d{1,2}日)?(?:[〜～\-~から以降]|頃)?(?:稼[動働]?可?)?")
_IMMEDIATE_RE = re.compile(r"即日|即時|即|今すぐ|すぐ|今月|today", re.IGNORECASE)
_YEAR_MONTH_RE = re.compile(r"(\d{4})[年/\-](\d{1,2})月?")


def _infer_year(month: int, reference_year: int | None = None) -> int:
    base_year = reference_year or _TODAY.year
    if month >= _TODAY.month:
        return base_year
    return base_year + 1


def _parse_received_year(received_date: str | None) -> int | None:
    if not received_date:
        return None
    m = re.search(r"(\d{4})", received_date)
    return int(m.group(1)) if m else None


def _safe_date(year: int, month: int, day: int = 1) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def extract_availability(parsed: ParsedEngineerText) -> AvailabilityResult:
    ref_year = _parse_received_year(parsed.received_date)

    for key in ("開始", "稼動可能日", "稼働可能日"):
        if key in parsed.labeled_fields:
            text = parsed.labeled_fields[key]
            r = _parse_date_from_text(text, ref_year)
            if r:
                r.source = "labeled"
                return r

    for text, src in [
        (parsed.subject or "", "subject"),
        (parsed.body or parsed.full_text, "body"),
    ]:
        if not text:
            continue
        r = _parse_date_from_text(text, ref_year)
        if r:
            r.source = src
            return r

    return AvailabilityResult(confidence=0.0, source="none")


def _parse_date_from_text(text: str, ref_year: int | None) -> AvailabilityResult | None:
    # immediate
    if _IMMEDIATE_RE.search(text):
        return AvailabilityResult(
            start_date=_TODAY.isoformat(),
            is_immediate=True,
            confidence=0.90,
            evidence=text[:50],
        )

    # full ISO date: 2026/07/01 or 2026年7月1日
    m = _ISO_DATE_RE.search(text)
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            return AvailabilityResult(
                start_date=d, confidence=0.92, evidence=m.group(0)
            )

    # year+month only: 2026年7月
    m = _YEAR_MONTH_RE.search(text)
    if m:
        d = _safe_date(int(m.group(1)), int(m.group(2)))
        if d:
            return AvailabilityResult(
                start_date=d, confidence=0.88, evidence=m.group(0)
            )

    # month only: 7月〜
    m = _MONTH_ONLY_RE.search(text)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            year = _infer_year(month, ref_year)
            d = _safe_date(year, month)
            if d:
                return AvailabilityResult(
                    start_date=d,
                    inferred_year=True,
                    confidence=0.75,
                    evidence=m.group(0),
                )

    return None
