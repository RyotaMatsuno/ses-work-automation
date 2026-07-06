"""Merge policy — fill empty, never overwrite."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


@dataclass
class MergeDecision:
    field: str
    action: str  # "update" | "skip_existing" | "skip_no_value" | "conflict"
    old_value: Any
    new_value: Any
    confidence: float
    source: str


def _is_empty(value: Any, field: str = "") -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    # 単価0 is treated as empty
    if field in ("単価（万円）",) and value == 0:
        return True
    return False


_FIELD_MIN_CONFIDENCE: dict[str, float] = {
    "経験年数": 0.70,
    "最寄り駅": 0.65,
}


def decide_merge(
    existing_props: dict[str, Any],
    extracted: dict[str, Any],
    confidences: dict[str, float] | None = None,
    sources: dict[str, str] | None = None,
) -> list[MergeDecision]:
    decisions: list[MergeDecision] = []
    confidences = confidences or {}
    sources = sources or {}

    for field, new_val in extracted.items():
        old_val = existing_props.get(field)
        conf = confidences.get(field, 0.0)
        source = sources.get(field, "unknown")
        min_conf = _FIELD_MIN_CONFIDENCE.get(field, 0.5)

        if new_val is None or (isinstance(new_val, list) and not new_val):
            decisions.append(MergeDecision(
                field=field, action="skip_no_value",
                old_value=old_val, new_value=new_val,
                confidence=conf, source=source,
            ))
            continue

        if conf < min_conf:
            decisions.append(MergeDecision(
                field=field, action="skip_no_value",
                old_value=old_val, new_value=new_val,
                confidence=conf, source=source,
            ))
            continue

        if _is_empty(old_val, field):
            decisions.append(MergeDecision(
                field=field, action="update",
                old_value=old_val, new_value=new_val,
                confidence=conf, source=source,
            ))
        else:
            decisions.append(MergeDecision(
                field=field, action="skip_existing",
                old_value=old_val, new_value=new_val,
                confidence=conf, source=source,
            ))

    return decisions
