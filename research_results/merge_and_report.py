# -*- coding: utf-8 -*-
"""データ統合 + サマリーレポート生成"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

from crawl_common import BASE_DIR, read_csv, today_str, write_csv

OUT_FULL = BASE_DIR / "ses_sales_compensation_full_survey.csv"
OUT_SUMMARY = BASE_DIR / "survey_summary.md"
PHASE3_JSONL = BASE_DIR / "phase3_extracted.jsonl"
PHASE3_CSV = BASE_DIR / "phase3_extracted.csv"

FULL_FIELDS = [
    "company_name",
    "employment_type",
    "base_salary_monthly",
    "incentive_description",
    "incentive_rate_pct",
    "incentive_base",
    "incentive_type",
    "incentive_cap",
    "expected_annual_min",
    "expected_annual_max",
    "has_quota",
    "required_experience",
    "employee_count",
    "founded_year",
    "hq_location",
    "remote_policy",
    "notes",
    "source_url",
    "crawl_date",
    "data_source",
]


def _load_phase3() -> pd.DataFrame:
    if PHASE3_JSONL.exists():
        rows = []
        for line in PHASE3_JSONL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        if rows:
            return pd.DataFrame(rows)
    if PHASE3_CSV.exists():
        return pd.read_csv(PHASE3_CSV, encoding="utf-8-sig")
    return pd.DataFrame()


def _phase2_to_rows(path: Path, source: str) -> list[dict]:
    rows = []
    for r in read_csv(path):
        rows.append(
            {
                "company_name": r.get("company_name", ""),
                "employment_type": r.get("employment_type", ""),
                "base_salary_monthly": None,
                "incentive_description": r.get("incentive_text", ""),
                "incentive_rate_pct": None,
                "incentive_base": "不明",
                "incentive_type": "不明",
                "incentive_cap": "不明",
                "expected_annual_min": None,
                "expected_annual_max": None,
                "has_quota": "不明",
                "required_experience": "",
                "employee_count": r.get("employee_count") or None,
                "founded_year": r.get("founded_year") or None,
                "hq_location": r.get("location", ""),
                "remote_policy": "不明",
                "notes": r.get("salary_text", ""),
                "source_url": r.get("job_url", ""),
                "crawl_date": r.get("crawl_date", today_str()),
                "data_source": source,
            }
        )
    return rows


def merge_all() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []

    p3 = _load_phase3()
    if not p3.empty:
        p3["data_source"] = "phase3_llm"
        frames.append(p3)

    for path, src in [
        (BASE_DIR / "phase2_engage.csv", "phase2_engage"),
        (BASE_DIR / "phase2_green.csv", "phase2_green"),
    ]:
        if path.exists():
            frames.append(pd.DataFrame(_phase2_to_rows(path, src)))

    if not frames:
        return pd.DataFrame(columns=FULL_FIELDS)

    df = pd.concat(frames, ignore_index=True)
    if "source_url" in df.columns:
        df = df.drop_duplicates(subset=["source_url"], keep="first")
    return df


def _rate_histogram(df: pd.DataFrame) -> str:
    rates = pd.to_numeric(df.get("incentive_rate_pct"), errors="coerce").dropna()
    if rates.empty:
        return "（インセンティブ率の数値データなし）\n"
    bins = [0, 10, 15, 20, 25, 30, 35, 40, 50, 100]
    labels = ["0-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35-40", "40-50", "50+"]
    cats = pd.cut(rates, bins=bins, labels=labels, right=False)
    counts = cats.value_counts().sort_index()
    lines = ["| 還元率帯 | 件数 |", "|---|---|"]
    for label, cnt in counts.items():
        lines.append(f"| {label}% | {int(cnt)} |")
    return "\n".join(lines) + "\n"


def generate_summary(df: pd.DataFrame) -> str:
    total = len(df)
    unique_companies = df["company_name"].nunique() if "company_name" in df.columns else 0
    emp_counts = Counter(df["employment_type"].fillna("不明")) if "employment_type" in df.columns else Counter()

    rates = pd.to_numeric(df.get("incentive_rate_pct"), errors="coerce")
    high_rate = df[rates >= 30].copy() if not rates.empty else df.iloc[0:0]

    no_rate = df[
        df["incentive_rate_pct"].isna()
        & (df.get("incentive_description", pd.Series(dtype=str)).fillna("") == "")
    ]

    unknown_incentive = df[
        df["incentive_rate_pct"].isna()
        & df.get("incentive_description", pd.Series(dtype=str)).fillna("").str.contains("インセンティブ|粗利|歩合", regex=True, na=False)
    ]

    lines = [
        "# SES営業求人 報酬調査サマリー",
        "",
        f"生成日: {today_str()}",
        "",
        "## 概要",
        f"- 総求人数: **{total}**",
        f"- ユニーク企業数（会社名ベース）: **{unique_companies}**",
        "",
        "## 雇用形態別件数",
        "",
    ]
    for k, v in emp_counts.most_common():
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        "## インセンティブ率分布",
        "",
        _rate_histogram(df),
        "",
        f"## 粗利30%以上の企業（{len(high_rate)}件）",
        "",
    ]
    if len(high_rate):
        for _, row in high_rate.head(50).iterrows():
            lines.append(
                f"- {row.get('company_name','')} | {row.get('incentive_rate_pct','')}% | {row.get('source_url','')}"
            )
    else:
        lines.append("（該当なし）")

    lines += [
        "",
        "## インセンティブ条件",
        f"- 率・説明ともに非公開/不明: {len(no_rate)}件 ({(len(no_rate)/total*100 if total else 0):.1f}%)",
        f"- 説明あり・率不明: {len(unknown_incentive)}件",
        "",
        "## データソース内訳",
    ]
    if "data_source" in df.columns:
        for k, v in Counter(df["data_source"]).most_common():
            lines.append(f"- {k}: {v}")

    return "\n".join(lines) + "\n"


def main() -> int:
    df = merge_all()
    if df.empty:
        print("No data to merge")
        return 1

    for col in FULL_FIELDS:
        if col not in df.columns:
            df[col] = None
    df = df[FULL_FIELDS]
    df.to_csv(OUT_FULL, index=False, encoding="utf-8-sig")

    summary = generate_summary(df)
    OUT_SUMMARY.write_text(summary, encoding="utf-8")

    print(f"ses_sales_compensation_full_survey.csv: {len(df)} rows")
    print(f"survey_summary.md written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
