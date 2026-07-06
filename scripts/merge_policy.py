# -*- coding: utf-8 -*-
"""Field-level merge policy for R5 backfill."""

from __future__ import annotations

MERGE_RULES = {
    "fill_if_empty": ["rate_type", "remote_type", "勤務地"],
    "replace_if_higher_confidence": ["単価（万円）"],
    "never_overwrite": ["必要スキル", "尚可スキル", "案件詳細", "案件名"],
    "flag_only": ["extraction_confidence", "needs_review"],
}

REPLACE_ZERO_FIELDS = {"単価（万円）"}

ALLOWED_OVERWRITE_REASONS = frozenset({
    "fill_if_empty",
    "replace_zero_with_extracted",
    "zero_to_null",
    "flag_only",
    "fix_anomaly_rate",
    "fix_anomaly_rate_type",
    "fill_if_empty_default",
})


def _is_rate_anomaly(value) -> bool:
    if not isinstance(value, (int, float)):
        return False
    return value > 200 or value == 0


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple, set)) and len(value) == 0:
        return True
    if isinstance(value, (int, float)) and value == 0:
        return True
    return False


def should_update(
    field_name: str,
    old_value,
    new_value,
    new_confidence: float,
    old_confidence: float | None = None,
) -> tuple[bool, str]:
    """Return whether to update a field and the reason."""
    if field_name in MERGE_RULES["never_overwrite"]:
        return False, "never_overwrite"

    if field_name in MERGE_RULES["flag_only"]:
        return True, "flag_only"

    if field_name in REPLACE_ZERO_FIELDS:
        if _is_rate_anomaly(old_value) and new_value is not None and new_value <= 200:
            return True, "fix_anomaly_rate"
        if _is_empty(old_value) and not _is_empty(new_value):
            return True, "replace_zero_with_extracted"
        if old_value == 0 and new_value is None:
            return True, "zero_to_null"
        if old_confidence is None:
            old_confidence = 0.0
        if not _is_empty(old_value) and not _is_empty(new_value):
            if new_confidence > old_confidence:
                return True, "replace_if_higher_confidence"
        return False, "keep_existing_rate"

    if field_name in MERGE_RULES["fill_if_empty"]:
        if (
            field_name == "rate_type"
            and old_value == "skill_dependent_no_number"
            and new_value == "skill_dependent_with_cap"
        ):
            return True, "fix_anomaly_rate_type"
        if _is_empty(old_value) and not _is_empty(new_value):
            return True, "fill_if_empty"
        return False, "keep_existing"

    if field_name in MERGE_RULES["replace_if_higher_confidence"]:
        if _is_empty(old_value) and not _is_empty(new_value):
            return True, "fill_if_empty"
        if old_confidence is None:
            old_confidence = 0.0
        if not _is_empty(new_value) and new_confidence > old_confidence:
            return True, "replace_if_higher_confidence"
        return False, "keep_existing"

    if _is_empty(old_value) and not _is_empty(new_value):
        return True, "fill_if_empty_default"
    return False, "no_rule"
