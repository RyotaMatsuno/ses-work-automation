"""Compute engineer DB field fill rates for F5 metrics."""
from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from update_runner import _fetch_all_engineers, _get_text_prop, _get_number_prop, _get_multi_select_prop, _get_date_prop


def _filled(props: dict, field: str) -> bool:
    if field == "スキル":
        return bool(_get_multi_select_prop(props, field))
    if field == "単価（万円）":
        v = _get_number_prop(props, field)
        return v is not None and v > 0
    if field == "最寄り駅":
        return bool(_get_text_prop(props, field).strip())
    if field == "経験年数":
        return _get_number_prop(props, field) is not None
    if field == "稼働可能日":
        return _get_date_prop(props, field) is not None
    return False


def main() -> None:
    records = _fetch_all_engineers()
    fields = ["スキル", "単価（万円）", "最寄り駅", "経験年数", "稼働可能日"]
    total = len(records)
    print(f"Total records: {total}")
    for field in fields:
        filled = sum(1 for r in records if _filled(r.get("properties", {}), field))
        empty = total - filled
        print(f"  {field}: filled={filled} empty={empty} ({filled/total*100:.1f}%)")


if __name__ == "__main__":
    main()
