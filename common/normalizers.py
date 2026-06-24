from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)
JST = timezone(timedelta(hours=9))

_SKILL_BASED_RE = re.compile(r"スキル見合い|応相談|精査|お見合い", re.IGNORECASE)
_RANGE_RE = re.compile(
    r"(?P<min>\d+(?:\.\d+)?)\s*(?:万)?\s*[-〜~－]\s*(?P<max>\d+(?:\.\d+)?)\s*万?",
)
_SINGLE_RE = re.compile(r"(?P<val>\d+(?:\.\d+)?)\s*万|(?P<yen>\d{4,})")
_UPPER_ONLY_RE = re.compile(r"[〜~～]\s*(\d+(?:\.\d+)?)\s*万")


def _to_man(value: float) -> float:
    return value / 10000 if value >= 1000 else value


def normalize_rate(value: Any) -> tuple[float | None, float | None]:
    """単価表現を万円単位の (min, max) に正規化する。"""
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    if _SKILL_BASED_RE.search(text):
        return None, None

    range_match = _RANGE_RE.search(text.replace(",", ""))
    if range_match:
        low = _to_man(float(range_match.group("min")))
        high = _to_man(float(range_match.group("max")))
        return low, high

    upper = _UPPER_ONLY_RE.search(text.replace(",", ""))
    if upper:
        return None, _to_man(float(upper.group(1)))

    single = _SINGLE_RE.search(text.replace(",", ""))
    if single:
        if single.group("yen"):
            val = _to_man(float(single.group("yen")))
        else:
            val = _to_man(float(single.group("val")))
        return val, val

    try:
        val = float(text)
    except (TypeError, ValueError):
        return None, None
    val = _to_man(val)
    return val, val


def normalize_rate_fields(
    min_value: Any,
    max_value: Any,
) -> tuple[float | None, float | None, list[str]]:
    """min/max を正規化し、逆転時は swap する。"""
    warnings: list[str] = []
    if min_value is not None and max_value is not None:
        try:
            pmin = float(min_value)
            pmax = float(max_value)
        except (TypeError, ValueError):
            pmin, pmax = normalize_rate(min_value)
            if pmax is None:
                _, pmax = normalize_rate(max_value)
        else:
            if pmin >= 1000:
                pmin = pmin / 10000
            if pmax >= 1000:
                pmax = pmax / 10000
    elif min_value is not None:
        pmin, pmax = normalize_rate(min_value)
    elif max_value is not None:
        pmin, pmax = normalize_rate(max_value)
    else:
        return None, None, warnings

    if pmin is not None and pmax is not None and pmax < pmin:
        warnings.append(f"単価レンジ逆転を補正: {pmin}↔{pmax}")
        pmin, pmax = pmax, pmin
    return pmin, pmax, warnings


def normalize_availability(value: Any, *, today: date | None = None) -> str | None:
    """稼働開始時期を正規化する。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "即日" in text:
        return "即日"

    reference = today or datetime.now(JST).date()
    if "来月" in text:
        year = reference.year + (1 if reference.month == 12 else 0)
        month = 1 if reference.month == 12 else reference.month + 1
        return f"{year}-{month:02d}"

    month_match = re.search(r"(\d{1,2})\s*月", text)
    if month_match:
        month = int(month_match.group(1))
        year = reference.year
        if month < reference.month:
            year += 1
        return f"{year}-{month:02d}"

    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso_match:
        return iso_match.group(1)[:7]
    return text
