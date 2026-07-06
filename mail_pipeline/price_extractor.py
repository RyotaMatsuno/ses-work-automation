"""Rule-first price extraction for SES project emails."""

from __future__ import annotations

import re
import unicodedata


def validate_price(value: float | int | None, raw_text: str = "") -> tuple[float | None, str | None]:
    """単価の異常値を検出してnullまたは変換する。
    Returns: (validated_value_or_none, reason_or_none)
    reason: None=正常, 'annual_converted', 'daily_converted', 'anomaly_nulled'
    """
    if value is None:
        return None, None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None, "anomaly_nulled"
    if val > 200:
        annual_keywords = ["年収", "年俸", "賞与込", "annual"]
        if any(kw in raw_text for kw in annual_keywords):
            return round(val / 12, 1), "annual_converted"
        return None, "anomaly_nulled"
    if val < 20:
        daily_keywords = ["日額", "日給", "/日", "daily"]
        if any(kw in raw_text for kw in daily_keywords):
            return round(val * 20, 1), "daily_converted"
        return None, "anomaly_nulled"
    return val, None


def extract_price(subject: str, body: str) -> dict:
    """Extract price from subject/body. Returns value, unit, raw, confidence."""
    result = _extract_from_text(subject or "")
    if result["value"] is not None:
        return result

    result = _extract_from_text((body or "")[:5000])
    if result["value"] is not None:
        return result

    for keyword in ("単価", "月額", "予算", "単金", "金額", "MAX", "Max", "max"):
        idx = (body or "").find(keyword)
        if idx >= 0:
            window = (body or "")[idx : idx + 120]
            result = _extract_from_text(window)
            if result["value"] is not None:
                return result

    return {"value": None, "unit": None, "raw": "", "confidence": "none"}


def resolve_final_price(ai_price: float | int | None, subject: str, body: str) -> float | None:
    """Merge AI price with rule-based extraction."""
    rule_result = extract_price(subject, body)
    ai_val = _coerce_price(ai_price)

    if rule_result["confidence"] == "high" and rule_result["unit"] == "monthly":
        return float(rule_result["value"])
    if ai_val is not None and 15 <= ai_val <= 200:
        return ai_val
    if rule_result["value"] is not None and rule_result["confidence"] != "suspicious":
        unit = rule_result.get("unit")
        if unit == "monthly":
            return float(rule_result["value"])
        if unit == "annual" and rule_result.get("normalized_monthly"):
            return float(rule_result["normalized_monthly"])
        if unit == "daily" and rule_result.get("normalized_monthly"):
            return float(rule_result["normalized_monthly"])
    return None


def _coerce_price(value: float | int | None) -> float | None:
    if value is None:
        return None
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    # Claude sometimes returns yen instead of 万円
    if price >= 1000:
        price = price / 10000
    return price


def _extract_from_text(text: str) -> dict:
    text = unicodedata.normalize("NFKC", text)

    _MAN = r"[\u4e07\u679c\u6b73果]"

    # Labeled price first (avoids false positives like "Microsoft 365/")
    m = re.search(
        rf"(?:単価|月額|予算|単金|金額)\s*[：:]\s*[＠@]?\s*"
        rf"(\d+(?:\.\d+)?)\s*(?:万|{_MAN})?(?:円)?",
        text,
    )
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(
        r"(?:予\s*算|単価|月額|金額)\s*[：:]\s*[＠@]?\s*"
        r"(\d{2,3})\s*[〜~～\-－]\s*(\d{2,3})(?!\s*[hH]|時間)",
        text,
    )
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(r"[＠@](\d{2,3})\s*程度", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(rf"(\d+(?:\.\d+)?)\s*[〜~～\-－]\s*(\d+(?:\.\d+)?)\s*(?:万|{_MAN})", text)
    if m:
        lower = float(m.group(1))
        return _classify(lower, text, m.group(0))

    m = re.search(rf"[Mm][Aa][Xx]\s*(\d+(?:\.\d+)?)\s*(?:万|{_MAN})?(?:円)?", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(rf"(\d{{2,3}})(?:万|{_MAN})?/(?:\u7537|\u5973|男|女)", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(r"`(\d{2,3})`", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(r"(\d{2,3})[`\u2019](\d{2,3})", text)
    if m:
        lower = float(m.group(1))
        return _classify(lower, text, m.group(0))

    m = re.search(r"[Mm][Aa][Xx](\d{2,3})\b", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(rf"[〜~～]\s*(\d+(?:\.\d+)?)\s*(?:万|{_MAN})(?:円)?", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    # Bare SES range without 万 (skip hour ranges like 140h-190h)
    for m in re.finditer(
        r"(?<![\d/.])(\d{2,3})\s*[〜~～\-－]\s*(\d{2,3})(?!\s*[hH]|時間|\d)",
        text,
    ):
        lower, upper = float(m.group(1)), float(m.group(2))
        if 50 <= lower <= 200 and 50 <= upper <= 250 and lower <= upper:
            return _classify(lower, text, m.group(0))

    m = re.search(rf"(\d+(?:\.\d+)?)\s*(?:万|{_MAN})(?:円)?(?:上限|まで|迄|程度|前後)?", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    m = re.search(r"(?:単価|月額|予算|単金)[：:\s]*(\d+(?:\.\d+)?)", text)
    if m:
        return _classify(float(m.group(1)), text, m.group(0))

    return {"value": None, "unit": None, "raw": "", "confidence": "none"}


def _classify(value: float, context: str, raw: str) -> dict:
    if re.search(r"年収|賞与|昇給|想定年収", context):
        return {
            "value": value,
            "unit": "annual",
            "raw": raw,
            "confidence": "high",
            "normalized_monthly": round(value / 12, 1),
        }

    if re.search(r"/日|日額|人日|日当", context):
        return {
            "value": value,
            "unit": "daily",
            "raw": raw,
            "confidence": "high",
            "normalized_monthly": round(value * 20, 1),
        }

    confidence = "high"
    if value > 200:
        confidence = "suspicious"
    elif value < 15:
        confidence = "suspicious"

    return {"value": value, "unit": "monthly", "raw": raw, "confidence": confidence}
