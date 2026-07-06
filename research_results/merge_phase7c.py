# -*- coding: utf-8 -*-
"""Phase 7C: 統合マスター作成"""
from __future__ import annotations

import argparse
import re

from crawl_common import BASE_DIR, read_csv, today_str, write_csv
from phase4_helpers import company_core, extract_rate_pct
from phase7_helpers import incentive_flags_from_text, progress_log

OUT_MASTER = BASE_DIR / "ses_company_master_all.csv"
MASTER_FIELDS = [
    "company_name",
    "company_core",
    "source_list",
    "has_sales_recruit",
    "incentive_disclosed",
    "incentive_rate",
    "location",
    "crawl_date",
]

SALES_HINT = re.compile(r"営業|コーディネーター|セールス|BP営業|SES営業", re.I)


def _load_phase7a() -> list[dict]:
    rows = []
    for path, src in [
        (BASE_DIR / "phase7a_ses_companies_master.csv", "phase7a"),
        (BASE_DIR / "phase7a_ses_beginner_list.csv", "ses_beginner"),
        (BASE_DIR / "phase7a_ses_media_list.csv", "ses_media"),
    ]:
        for r in read_csv(path):
            name = (r.get("company_name") or "").strip()
            if name:
                rows.append(
                    {
                        "company_name": name,
                        "source": src,
                        "location": r.get("location", ""),
                        "has_sales": False,
                        "incentive_text": "",
                    }
                )
    return rows


def _load_phase7b() -> list[dict]:
    rows = []
    for r in read_csv(BASE_DIR / "phase7b_kyujinbox_companies.csv"):
        name = (r.get("company_name") or "").strip()
        job = r.get("job_title", "")
        if name:
            rows.append(
                {
                    "company_name": name,
                    "source": "kyujinbox",
                    "location": "",
                    "has_sales": bool(SALES_HINT.search(job)),
                    "incentive_text": job,
                }
            )
    return rows


def _load_legacy() -> list[dict]:
    rows = []
    legacy_sources = [
        (BASE_DIR / "phase2_engage.csv", "company_name", "engage", "job_title"),
        (BASE_DIR / "phase3_extracted.csv", "company_name", "phase3", "incentive_description"),
        (BASE_DIR / "phase4e_company_hp_list.csv", "company_name", "phase4e", ""),
        (BASE_DIR / "phase6_detailed.csv", "company_name", "phase6", "incentive_text"),
    ]
    for path in BASE_DIR.glob("phase4a_*.csv"):
        legacy_sources.append((path, "company_name", f"phase4a_{path.stem.replace('phase4a_','')}", "incentive_text"))

    for path, name_f, src, text_f in legacy_sources:
        for r in read_csv(path):
            name = (r.get(name_f) or "").strip()
            if not name or len(name) < 2:
                continue
            text = r.get(text_f, "") if text_f else ""
            title = r.get("job_title", "") or r.get("notes", "")
            has_sales = bool(SALES_HINT.search(f"{title} {text}"))
            rows.append(
                {
                    "company_name": name,
                    "source": src,
                    "location": r.get("location", "") or r.get("hq_location", ""),
                    "has_sales": has_sales,
                    "incentive_text": f"{text} {r.get('incentive_text','')}",
                }
            )
    return rows


def build_master() -> list[dict]:
    all_in = _load_phase7a() + _load_phase7b() + _load_legacy()
    by_core: dict[str, dict] = {}

    for r in all_in:
        name = r["company_name"]
        core = company_core(name)
        if not core:
            continue
        src = r.get("source", "")
        if core not in by_core:
            by_core[core] = {
                "company_name": name,
                "company_core": core,
                "sources": set(),
                "has_sales": False,
                "incentive_texts": [],
                "location": r.get("location", ""),
            }
        by_core[core]["sources"].add(src)
        if r.get("has_sales"):
            by_core[core]["has_sales"] = True
        if r.get("incentive_text"):
            by_core[core]["incentive_texts"].append(r["incentive_text"])
        if r.get("location") and not by_core[core]["location"]:
            by_core[core]["location"] = r["location"]
        # prefer longer official name
        if len(name) > len(by_core[core]["company_name"]):
            by_core[core]["company_name"] = name

    out: list[dict] = []
    for core, info in by_core.items():
        combined_text = " ".join(info["incentive_texts"])
        disclosed, rate = incentive_flags_from_text(combined_text)
        has_sales = info["has_sales"]
        if has_sales:
            sales_flag = "あり"
        elif any(s.startswith("phase7a") or s in ("ses_beginner", "ses_media") for s in info["sources"]):
            sales_flag = "不明"
        else:
            sales_flag = "不明"

        out.append(
            {
                "company_name": info["company_name"],
                "company_core": core,
                "source_list": ";".join(sorted(info["sources"])),
                "has_sales_recruit": sales_flag,
                "incentive_disclosed": disclosed if disclosed != "なし" else "なし" if not combined_text.strip() else "不明",
                "incentive_rate": rate or "",
                "location": info.get("location", ""),
                "crawl_date": today_str(),
            }
        )
    out.sort(key=lambda x: x["company_name"])
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    master = build_master()
    n = write_csv(OUT_MASTER, MASTER_FIELDS, master)
    print(f"ses_company_master_all.csv: {n} rows", flush=True)

    sales_yes = sum(1 for r in master if r["has_sales_recruit"] == "あり")
    inc_yes = sum(1 for r in master if r["incentive_disclosed"] == "あり")
    print(f"  sales_recruit=あり: {sales_yes}, incentive_disclosed=あり: {inc_yes}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
