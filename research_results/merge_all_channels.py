# -*- coding: utf-8 -*-
"""Phase 5: 全チャネル統合 + サマリーレポート"""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd

from crawl_common import BASE_DIR, read_csv, today_str, write_csv
from phase4_helpers import (
    PHASE4A_SITE_OUTPUT,
    SALES_HINT,
    company_core,
    extract_rate_pct,
    is_sales_job,
)

OUT_FULL = BASE_DIR / "ses_sales_all_channels_full.csv"
OUT_INCENTIVE = BASE_DIR / "ses_sales_incentive_detail.csv"
OUT_SUMMARY = BASE_DIR / "all_channels_survey_summary.md"
OUT_HP_LIST = BASE_DIR / "phase4e_company_hp_list.csv"

UNIFIED_FIELDS = [
    "company_name",
    "company_core",
    "job_title",
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
    "channel",
]


def _phase3_rows() -> list[dict]:
    path = BASE_DIR / "phase3_extracted.csv"
    if not path.exists():
        return []
    rows = []
    for r in read_csv(path):
        title = r.get("notes") or r.get("incentive_description") or ""
        text = f"{title} {r.get('incentive_description', '')}"
        if not is_sales_job(title, text):
            continue
        rate = r.get("incentive_rate_pct")
        try:
            rate_f = float(rate) if rate not in (None, "", "nan") else None
        except (ValueError, TypeError):
            rate_f = extract_rate_pct(text)
        rows.append(
            {
                "company_name": r.get("company_name", ""),
                "company_core": company_core(r.get("company_name", "")),
                "job_title": title[:300],
                "employment_type": r.get("employment_type", ""),
                "base_salary_monthly": r.get("base_salary_monthly"),
                "incentive_description": r.get("incentive_description", ""),
                "incentive_rate_pct": rate_f,
                "incentive_base": r.get("incentive_base", "不明"),
                "incentive_type": r.get("incentive_type", "不明"),
                "incentive_cap": r.get("incentive_cap", "不明"),
                "expected_annual_min": r.get("expected_annual_min"),
                "expected_annual_max": r.get("expected_annual_max"),
                "has_quota": r.get("has_quota", "不明"),
                "required_experience": r.get("required_experience", ""),
                "employee_count": r.get("employee_count"),
                "founded_year": r.get("founded_year"),
                "hq_location": r.get("hq_location", ""),
                "remote_policy": r.get("remote_policy", "不明"),
                "notes": r.get("notes", ""),
                "source_url": r.get("source_url", ""),
                "crawl_date": r.get("crawl_date", today_str()),
                "data_source": "phase3_engage",
                "channel": "engage",
            }
        )
    return rows


def _phase4a_rows() -> list[dict]:
    rows = []
    for fname, channel in [(v, k) for k, v in PHASE4A_SITE_OUTPUT.items()]:
        for r in read_csv(BASE_DIR / fname):
            text = r.get("raw_text", "")
            title = r.get("job_title", "")
            rate = extract_rate_pct(f"{r.get('incentive_text', '')} {text}")
            rows.append(
                {
                    "company_name": r.get("company_name", ""),
                    "company_core": company_core(r.get("company_name", "")),
                    "job_title": title,
                    "employment_type": r.get("employment_type", ""),
                    "base_salary_monthly": None,
                    "incentive_description": r.get("incentive_text", ""),
                    "incentive_rate_pct": rate,
                    "incentive_base": "粗利" if "粗利" in text else "不明",
                    "incentive_type": "ストック型" if "ストック" in text else "不明",
                    "incentive_cap": "上限なし" if "上限なし" in text else "不明",
                    "expected_annual_min": None,
                    "expected_annual_max": None,
                    "has_quota": "不明",
                    "required_experience": "",
                    "employee_count": None,
                    "founded_year": None,
                    "hq_location": r.get("location", ""),
                    "remote_policy": "不明",
                    "notes": r.get("salary_text", ""),
                    "source_url": r.get("job_url", ""),
                    "crawl_date": r.get("crawl_date", today_str()),
                    "data_source": f"phase4a_{channel}",
                    "channel": channel,
                }
            )
    return rows


def _phase4b_rows() -> list[dict]:
    rows = []
    for r in read_csv(BASE_DIR / "phase4b_sns_blog.csv"):
        text = f"{r.get('title', '')} {r.get('snippet', '')}"
        if not SALES_HINT.search(text):
            continue
        rate = extract_rate_pct(text)
        rows.append(
            {
                "company_name": r.get("company_name_if_found", ""),
                "company_core": company_core(r.get("company_name_if_found", "")),
                "job_title": r.get("title", ""),
                "employment_type": "",
                "base_salary_monthly": None,
                "incentive_description": r.get("snippet", ""),
                "incentive_rate_pct": rate,
                "incentive_base": "不明",
                "incentive_type": "不明",
                "incentive_cap": "不明",
                "expected_annual_min": None,
                "expected_annual_max": None,
                "has_quota": "不明",
                "required_experience": "",
                "employee_count": None,
                "founded_year": None,
                "hq_location": "",
                "remote_policy": "不明",
                "notes": r.get("search_query", ""),
                "source_url": r.get("url", ""),
                "crawl_date": r.get("crawl_date", today_str()),
                "data_source": f"phase4b_{r.get('source_type', 'sns')}",
                "channel": r.get("source_type", "sns"),
            }
        )
    return rows


def _phase4c_rows() -> list[dict]:
    rows = []
    for r in read_csv(BASE_DIR / "phase4c_company_hp.csv"):
        text = r.get("raw_text", "")
        rate = extract_rate_pct(f"{r.get('incentive_text', '')} {text}")
        rows.append(
            {
                "company_name": r.get("company_name", ""),
                "company_core": company_core(r.get("company_name", "")),
                "job_title": "採用ページ",
                "employment_type": "",
                "base_salary_monthly": None,
                "incentive_description": r.get("incentive_text", ""),
                "incentive_rate_pct": rate,
                "incentive_base": "粗利" if "粗利" in text else "不明",
                "incentive_type": "ストック型" if "ストック" in text else "不明",
                "incentive_cap": "不明",
                "expected_annual_min": None,
                "expected_annual_max": None,
                "has_quota": "不明",
                "required_experience": "",
                "employee_count": None,
                "founded_year": None,
                "hq_location": "",
                "remote_policy": "不明",
                "notes": r.get("filter_reason", ""),
                "source_url": r.get("recruit_url", r.get("hp_url", "")),
                "crawl_date": r.get("crawl_date", today_str()),
                "data_source": "phase4c_company_hp",
                "channel": "company_hp",
            }
        )
    return rows


def _phase4d_rows() -> list[dict]:
    rows = []
    for r in read_csv(BASE_DIR / "phase4d_review_sites.csv"):
        text = f"{r.get('title', '')} {r.get('snippet', '')}"
        rate = extract_rate_pct(text)
        rows.append(
            {
                "company_name": r.get("company_name", ""),
                "company_core": company_core(r.get("company_name", "")),
                "job_title": r.get("title", ""),
                "employment_type": "",
                "base_salary_monthly": None,
                "incentive_description": r.get("snippet", ""),
                "incentive_rate_pct": rate,
                "incentive_base": "不明",
                "incentive_type": "不明",
                "incentive_cap": "不明",
                "expected_annual_min": None,
                "expected_annual_max": None,
                "has_quota": "不明",
                "required_experience": "",
                "employee_count": None,
                "founded_year": None,
                "hq_location": "",
                "remote_policy": "不明",
                "notes": r.get("site", ""),
                "source_url": r.get("url", ""),
                "crawl_date": r.get("crawl_date", today_str()),
                "data_source": f"phase4d_{r.get('site', 'review')}",
                "channel": r.get("site", "review"),
            }
        )
    return rows


def _phase4e_hp_stats() -> dict:
    """Phase 4E 採用HPリストの統計（存在する場合）。"""
    if not OUT_HP_LIST.exists():
        return {"total": 0, "corporate": 0, "recruit": 0, "ses_sales": 0}
    rows = read_csv(OUT_HP_LIST)
    return {
        "total": len(rows),
        "corporate": sum(1 for r in rows if r.get("corporate_url")),
        "recruit": sum(1 for r in rows if r.get("recruit_url")),
        "ses_sales": sum(1 for r in rows if r.get("ses_sales_recruit_url")),
    }


def _classify_model(row: dict) -> str:
    text = f"{row.get('incentive_description', '')} {row.get('job_title', '')} {row.get('notes', '')}"
    rate = row.get("incentive_rate_pct")
    if rate and float(rate) >= 58:
        return "高還元型(58%以上)"
    if rate and float(rate) >= 30:
        return "中高還元型(30-57%)"
    if "ストック" in text:
        return "ストック型"
    if re.search(r"歩合|成果報酬|インセンティブ", text):
        return "歩合・成果報酬型"
    if "固定" in text and "インセンティブ" not in text:
        return "固定給中心"
    if not text.strip() or text.strip() == "不明":
        return "非公開/不明"
    return "その他"


def merge_all() -> pd.DataFrame:
    all_rows = (
        _phase3_rows()
        + _phase4a_rows()
        + _phase4b_rows()
        + _phase4c_rows()
        + _phase4d_rows()
    )
    if not all_rows:
        return pd.DataFrame(columns=UNIFIED_FIELDS)

    df = pd.DataFrame(all_rows)
    for col in UNIFIED_FIELDS:
        if col not in df.columns:
            df[col] = None
    df = df[UNIFIED_FIELDS]

    # URL重複排除
    df = df.drop_duplicates(subset=["source_url"], keep="first")

    # 会社名コアで名寄せカウント用列は既にある
    return df


def _has_explicit_incentive(row: pd.Series) -> bool:
    desc = str(row.get("incentive_description", "") or "")
    rate = row.get("incentive_rate_pct")
    if pd.notna(rate) and float(rate) > 0:
        return True
    return bool(re.search(r"インセンティブ|粗利|歩合|還元|成果報酬", desc))


def generate_summary(df: pd.DataFrame) -> str:
    total = len(df)
    unique_companies = df[df["company_core"] != ""]["company_core"].nunique()

    channel_counts = Counter(df["channel"].fillna("unknown"))
    source_counts = Counter(df["data_source"].fillna("unknown"))

    rates = pd.to_numeric(df["incentive_rate_pct"], errors="coerce")
    high_30 = df[rates >= 30].copy()
    matsuno = df[rates >= 58].copy()

    explicit = df[df.apply(_has_explicit_incentive, axis=1)]

    model_types = Counter(_classify_model(row) for _, row in df.iterrows())
    hp_stats = _phase4e_hp_stats()

    lines = [
        "# SES営業報酬 全チャネル調査サマリー",
        "",
        f"生成日: {today_str()}",
        "",
        "## 概要",
        f"- 総レコード数（営業職フィルタ後）: **{total}**",
        f"- ユニーク企業数（名寄せ後）: **{unique_companies}**",
        f"- インセンティブ明示レコード: **{len(explicit)}**",
        "",
        "## チャネル別収集件数",
        "",
    ]
    for k, v in channel_counts.most_common():
        lines.append(f"- {k}: {v}")

    lines += ["", "## データソース内訳", ""]
    for k, v in source_counts.most_common():
        lines.append(f"- {k}: {v}")

    lines += ["", "## インセンティブ率分布", "", "| 還元率帯 | 件数 |", "|---|---|"]
    bins = [(0, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 50), (50, 58), (58, 100)]
    for lo, hi in bins:
        cnt = int(((rates >= lo) & (rates < hi)).sum())
        label = f"{lo}-{hi}%" if hi < 100 else f"{lo}%+"
        lines.append(f"| {label} | {cnt} |")

    lines += [
        "",
        f"## 粗利30%以上の企業（{len(high_30)}件）",
        "",
    ]
    if len(high_30):
        for _, row in high_30.iterrows():
            lines.append(
                f"- {row.get('company_name','')} | {row.get('incentive_rate_pct','')}% | "
                f"{row.get('channel','')} | {row.get('source_url','')}"
            )
    else:
        lines.append("（該当なし）")

    lines += [
        "",
        "## 松野モデル（粗利58〜70%還元）以上の企業",
        "",
    ]
    if len(matsuno):
        lines.append(f"**{len(matsuno)}件の前例あり**")
        for _, row in matsuno.iterrows():
            lines.append(
                f"- {row.get('company_name','')} | {row.get('incentive_rate_pct','')}% | "
                f"{row.get('channel','')} | {row.get('source_url','')}"
            )
    else:
        lines.append("**営業職における58%以上還元の明示的前例は確認できず**")

    lines += ["", "## 業界の報酬モデル類型と割合", ""]
    for k, v in model_types.most_common():
        pct = v / total * 100 if total else 0
        lines.append(f"- {k}: {v}件 ({pct:.1f}%)")

    lines += [
        "",
        "## Phase 4E 採用HPリスト",
        "",
        f"- 出力ファイル: `{OUT_HP_LIST.name}`",
        f"- 登録企業数: **{hp_stats['total']}**",
        f"- 公式HP特定: **{hp_stats['corporate']}** ({hp_stats['corporate'] / hp_stats['total'] * 100 if hp_stats['total'] else 0:.1f}%)",
        f"- 採用ページ特定: **{hp_stats['recruit']}**",
        f"- SES営業募集ページあり: **{hp_stats['ses_sales']}**",
        "",
        "## Phase 4A 求人サイト別収集件数",
        "",
    ]
    phase4a_channels = Counter(
        r.get("channel", "")
        for r in _phase4a_rows()
        if r.get("channel")
    )
    if phase4a_channels:
        for k, v in phase4a_channels.most_common():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("（Phase 4A CSV未生成）")

    return "\n".join(lines) + "\n"


def main() -> int:
    df = merge_all()
    if df.empty:
        print("No data to merge", flush=True)
        return 1

    write_csv(OUT_FULL, UNIFIED_FIELDS, df.to_dict(orient="records"))

    explicit_df = df[df.apply(_has_explicit_incentive, axis=1)]
    write_csv(OUT_INCENTIVE, UNIFIED_FIELDS, explicit_df.to_dict(orient="records"))

    summary = generate_summary(df)
    OUT_SUMMARY.write_text(summary, encoding="utf-8")

    print(f"ses_sales_all_channels_full.csv: {len(df)} rows", flush=True)
    print(f"ses_sales_incentive_detail.csv: {len(explicit_df)} rows", flush=True)
    if OUT_HP_LIST.exists():
        hp = _phase4e_hp_stats()
        print(f"phase4e_company_hp_list.csv: {hp['total']} companies", flush=True)
    print(f"all_channels_survey_summary.md written", flush=True)
    print("\n===== all_channels_survey_summary.md =====\n", flush=True)
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
