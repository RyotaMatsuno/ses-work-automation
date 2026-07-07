# -*- coding: utf-8 -*-
"""Phase 9C-1: Phase 9A/9B と既存マスターの名寄せ → 新規企業抽出"""
from __future__ import annotations

import argparse

from crawl_common import read_csv, today_str, write_csv
from phase4_helpers import company_core
from phase9_helpers import FIELDS_NEW, MASTER_FINAL, OUT_9A, OUT_9B, OUT_NEW


def _load_api_rows() -> list[dict]:
    rows: list[dict] = []
    for path, src in [(OUT_9A, "gbizinfo"), (OUT_9B, "nta_houjin_bangou")]:
        for r in read_csv(path):
            name = (r.get("name") or r.get("company_name") or "").strip()
            if not name:
                continue
            rows.append(
                {
                    "company_name": name,
                    "company_core": company_core(name),
                    "corporate_number": (r.get("corporate_number") or "").strip(),
                    "location": (r.get("location") or "").strip(),
                    "employee_number": (r.get("employee_number") or "").strip(),
                    "capital_stock": (r.get("capital_stock") or "").strip(),
                    "date_of_establishment": (r.get("date_of_establishment") or "").strip(),
                    "business_summary": (r.get("business_summary") or "").strip(),
                    "source_list": src,
                    "crawl_date": r.get("crawl_date") or today_str(),
                }
            )
    return rows


def extract_new_companies() -> list[dict]:
    existing_cores: set[str] = set()
    existing_corps: set[str] = set()
    for r in read_csv(MASTER_FINAL):
        core = (r.get("company_core") or company_core(r.get("company_name", ""))).strip()
        if core:
            existing_cores.add(core)
        corp = (r.get("corporate_number") or "").strip()
        if corp:
            existing_corps.add(corp)

    merged: dict[str, dict] = {}
    for r in _load_api_rows():
        core = r["company_core"]
        corp = r.get("corporate_number", "")
        if not core:
            continue
        if core in existing_cores:
            continue
        if corp and corp in existing_corps:
            continue
        if core in merged:
            prev = merged[core]
            prev["source_list"] = ";".join(sorted(set(filter(None, [prev["source_list"], r["source_list"]]))))
            if not prev.get("corporate_number") and corp:
                prev["corporate_number"] = corp
            if not prev.get("location") and r.get("location"):
                prev["location"] = r["location"]
            continue
        merged[core] = r

    return sorted(merged.values(), key=lambda x: x["company_name"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge Phase 9 API results with master")
    args = parser.parse_args()

    if not MASTER_FINAL.exists():
        print(f"{MASTER_FINAL.name} not found.", flush=True)
        return 1

    new_rows = extract_new_companies()
    write_csv(OUT_NEW, FIELDS_NEW, new_rows)
    print(
        f"{OUT_NEW.name}: {len(new_rows)} new companies "
        f"(master={len(read_csv(MASTER_FINAL))})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
