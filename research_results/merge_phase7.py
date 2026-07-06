# -*- coding: utf-8 -*-
"""Phase 7 最終統合 + サマリーレポート"""
from __future__ import annotations

import argparse

from crawl_common import BASE_DIR, read_csv, today_str, write_csv
from merge_phase7d import merge_parts
from phase4_helpers import company_core

OUT_FINAL = BASE_DIR / "ses_company_master_final.csv"
OUT_SUMMARY = BASE_DIR / "phase7_final_summary.md"

FINAL_FIELDS = [
    "company_name",
    "company_core",
    "source_list",
    "has_sales_recruit",
    "incentive_disclosed",
    "incentive_rate",
    "location",
    "bing_snippet",
    "has_incentive_mention",
    "incentive_detail",
    "screened_date",
    "crawl_date",
]

POPULATION_ESTIMATE = 10_000


def build_final() -> list[dict]:
    master = {r.get("company_core") or company_core(r.get("company_name", "")): r for r in read_csv(BASE_DIR / "ses_company_master_all.csv")}
    screening = {
        r.get("company_core") or company_core(r.get("company_name", "")): r
        for r in merge_parts()
    }

    out: list[dict] = []
    all_cores = set(master.keys()) | set(screening.keys())
    for core in sorted(all_cores):
        if not core:
            continue
        m = master.get(core, {})
        s = screening.get(core, {})
        rate = m.get("incentive_rate") or s.get("incentive_rate") or ""
        disclosed = m.get("incentive_disclosed", "不明")
        if s.get("has_incentive_mention") == "yes" and disclosed == "不明":
            disclosed = "あり"
        if s.get("incentive_rate") and not rate:
            rate = s.get("incentive_rate")

        out.append(
            {
                "company_name": m.get("company_name") or s.get("company_name", ""),
                "company_core": core,
                "source_list": m.get("source_list", ""),
                "has_sales_recruit": m.get("has_sales_recruit", "不明"),
                "incentive_disclosed": disclosed,
                "incentive_rate": rate,
                "location": m.get("location", ""),
                "bing_snippet": s.get("bing_snippet", ""),
                "has_incentive_mention": s.get("has_incentive_mention", ""),
                "incentive_detail": s.get("incentive_detail", ""),
                "screened_date": s.get("screened_date", ""),
                "crawl_date": m.get("crawl_date", today_str()),
            }
        )
    return out


def _rate_float(row: dict) -> float | None:
    v = row.get("incentive_rate")
    if v in (None, "", "nan"):
        # try bing detail
        import re

        m = re.search(r"(\d{1,2})", str(row.get("incentive_detail", "")))
        if m:
            return float(m.group(1))
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def generate_summary(rows: list[dict]) -> str:
    total = len(rows)
    sales_yes = sum(1 for r in rows if r.get("has_sales_recruit") == "あり")
    inc_disclosed = sum(1 for r in rows if r.get("incentive_disclosed") == "あり")
    inc_mention = sum(1 for r in rows if r.get("has_incentive_mention") == "yes")
    rates = [_rate_float(r) for r in rows]
    rate_explicit = sum(1 for r in rates if r is not None)
    high_30 = sum(1 for r in rates if r is not None and r >= 30)
    high_58 = sum(1 for r in rates if r is not None and r >= 58)
    coverage = total / POPULATION_ESTIMATE * 100 if POPULATION_ESTIMATE else 0

    lines = [
        "# Phase 7 SES企業全数調査 サマリー",
        "",
        f"生成日: {today_str()}",
        "",
        "## 概要",
        f"- SES企業マスター総数: **{total}**",
        f"- 推定母集団（10,000社）に対する網羅率: **{coverage:.1f}%**",
        "",
        "## 営業求人・インセンティブ",
        f"- SES営業求人あり: **{sales_yes}**",
        f"- インセンティブ条件公開（既存+スクリーニング）: **{inc_disclosed}**",
        f"- Bingスクリーニングでインセンティブ言及: **{inc_mention}**",
        f"- 粗利%明示: **{rate_explicit}**",
        f"- 粗利30%以上: **{high_30}**",
        f"- 粗利58%以上: **{high_58}**",
        "",
        "## データソース",
        f"- phase7a_ses_companies_master.csv",
        f"- phase7b_kyujinbox_companies.csv",
        f"- Phase 1-6 既存データ",
        f"- phase7d_screening_results.csv",
        "",
        "## 出力ファイル",
        f"- `{OUT_FINAL.name}`",
        f"- `{OUT_SUMMARY.name}`",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    if not (BASE_DIR / "ses_company_master_all.csv").exists():
        print("ses_company_master_all.csv not found. Run merge_phase7c.py first.", flush=True)
        return 1

    final = build_final()
    write_csv(OUT_FINAL, FINAL_FIELDS, final)
    summary = generate_summary(final)
    OUT_SUMMARY.write_text(summary, encoding="utf-8")

    print(f"ses_company_master_final.csv: {len(final)} rows", flush=True)
    print(f"phase7_final_summary.md written", flush=True)
    print("\n===== phase7_final_summary.md =====\n", flush=True)
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
