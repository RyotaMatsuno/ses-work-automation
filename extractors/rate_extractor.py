"""Rule-based rate extraction from SES project text (values always in 万円)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

RATE_TYPE_FIXED_RANGE = "fixed_range"
RATE_TYPE_FIXED_UPPER_ONLY = "fixed_upper_only"
RATE_TYPE_FIXED_LOWER_ONLY = "fixed_lower_only"
RATE_TYPE_SKILL_CAP = "skill_dependent_with_cap"
RATE_TYPE_SKILL_NO_NUMBER = "skill_dependent_no_number"
RATE_TYPE_NOT_PRESENT = "not_present"
RATE_TYPE_UNKNOWN = "unknown"

_RATE_HINTS = ("予算", "金額", "単価", "単金", "月額", "報酬")
_WINDOW = 100

# (rate_type, pattern, confidence, kind) — kind: range | single | none
_PASS1_SPECS: list[tuple[str, str, float, str]] = [
    (
        RATE_TYPE_FIXED_RANGE,
        r"(\d{2,3})\s*万?円?\s*[〜～\-~]\s*(\d{2,3})\s*万",
        0.90,
        "range",
    ),
    (
        RATE_TYPE_FIXED_UPPER_ONLY,
        r"[〜～~]\s*(\d{2,3})\s*万",
        0.80,
        "single",
    ),
    (
        RATE_TYPE_SKILL_CAP,
        r"スキル見合.{0,80}?(?:MAX|max|Max|上限|〜|~|～|まで)?\s*(\d{2,3})\s*万",
        0.90,
        "single",
    ),
    (
        RATE_TYPE_SKILL_CAP,
        r"(\d{2,3})\s*万円?\s*[（(].{0,20}?(?:スキル見合|経験見合)",
        0.85,
        "single",
    ),
    (
        RATE_TYPE_FIXED_UPPER_ONLY,
        r"(?:MAX|max|Max|上限)\s*[:：]?\s*(\d{2,3})\s*万",
        0.85,
        "single",
    ),
    (
        RATE_TYPE_FIXED_UPPER_ONLY,
        r"(\d{2,3})\s*万円?\s*(?:まで|以下|以内)",
        0.80,
        "single",
    ),
    (
        RATE_TYPE_FIXED_UPPER_ONLY,
        r"(\d{2,3})\s*万円?\s*(?:前後|程度|目安|想定)",
        0.70,
        "single",
    ),
    (
        RATE_TYPE_FIXED_UPPER_ONLY,
        r"(?:単価|予算|金額|報酬)\s*[:：]\s*(\d{2,3})\s*万",
        0.75,
        "single",
    ),
    (
        RATE_TYPE_SKILL_NO_NUMBER,
        r"スキル見合|経験見合|ご経験見合|スキル次第",
        1.0,
        "none",
    ),
    (
        RATE_TYPE_SKILL_NO_NUMBER,
        r"応相談",
        0.80,
        "none",
    ),
]

_COMPILED = [
    (rt, re.compile(pat), conf, kind) for rt, pat, conf, kind in _PASS1_SPECS
]


@dataclass
class RateResult:
    rate_min_man: float | None = None
    rate_max_man: float | None = None
    rate_type: str = RATE_TYPE_NOT_PRESENT
    confidence: float = 0.0
    method: str = "regex"
    evidence: str | None = None
    needs_llm_fallback: bool = False
    needs_review: bool = False


def normalize_rate_text(text: str) -> str:
    """全角数字・スペースを半角に正規化。"""
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"(\d),(\d)", r"\1\2", normalized)


def validate_rate_man(value: float | None) -> float | None:
    """万単位の単価を書き込み前に検証。異常値は ValueError。"""
    if value is None:
        return None
    if value < 0:
        raise ValueError(f"rate < 0: {value}")
    if value > 200:
        raise ValueError(f"rate > 200 (possible unit conversion bug): {value}")
    return float(value)


def _clamp_rate(value: float | None) -> tuple[float | None, bool]:
    if value is None:
        return None, False
    needs_review = False
    try:
        validate_rate_man(value)
    except ValueError:
        return None, True
    if value < 10:
        needs_review = True
    return value, needs_review


def _windowed_search(text: str, pattern: re.Pattern[str]) -> re.Match[str] | None:
    """レート関連キーワード付近100文字窓、または全文でマッチ。"""
    for hint in _RATE_HINTS:
        start = 0
        while True:
            idx = text.find(hint, start)
            if idx < 0:
                break
            window = text[max(0, idx - 20) : idx + _WINDOW]
            m = pattern.search(window)
            if m:
                return m
            start = idx + len(hint)
    return pattern.search(text[:5000])


def extract_rate(text: str) -> RateResult:
    """Extract monthly rate (万円) and classification from text."""
    if not text or not text.strip():
        return RateResult(rate_type=RATE_TYPE_NOT_PRESENT, confidence=0.0)

    normalized = normalize_rate_text(text)
    if re.search(r"年収|年俸", normalized):
        return RateResult(
            rate_type=RATE_TYPE_UNKNOWN,
            confidence=0.2,
            needs_llm_fallback=True,
            needs_review=True,
        )

    for rate_type, pattern, confidence, kind in _COMPILED:
        match = _windowed_search(normalized, pattern)
        if not match:
            continue

        evidence = match.group(0).strip()
        result = RateResult(
            rate_type=rate_type,
            method="regex",
            evidence=evidence,
            confidence=confidence,
        )

        if kind == "range":
            raw_min = float(match.group(1))
            raw_max = float(match.group(2))
            if raw_min > raw_max:
                raw_min, raw_max = raw_max, raw_min
            min_val, min_review = _clamp_rate(raw_min)
            max_val, max_review = _clamp_rate(raw_max)
            result.rate_min_man = min_val
            result.rate_max_man = max_val
            result.needs_review = min_review or max_review
            return result

        if kind == "single":
            raw_max = float(match.group(1))
            max_val, review = _clamp_rate(raw_max)
            result.rate_max_man = max_val
            result.needs_review = review
            return result

        if kind == "none":
            return result

    has_hint = any(hint in normalized for hint in _RATE_HINTS)
    if has_hint:
        return RateResult(
            rate_type=RATE_TYPE_UNKNOWN,
            confidence=0.2,
            needs_llm_fallback=True,
        )

    return RateResult(rate_type=RATE_TYPE_NOT_PRESENT, confidence=0.5)
