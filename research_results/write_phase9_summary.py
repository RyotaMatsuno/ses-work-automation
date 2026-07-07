# -*- coding: utf-8 -*-
"""Phase 9 サマリーレポート生成"""
from __future__ import annotations

import argparse
import re

from crawl_common import read_csv, today_str
from phase9_helpers import (
    MASTER_FINAL,
    OUT_9A,
    OUT_9B,
    OUT_NEW,
    OUT_SCREENING,
    OUT_SUMMARY,
    POPULATION_ESTIMATE,
)


def _rate_float(row: dict) -> float | None:
    v = row.get("incentive_rate")
    if v not in (None, "", "nan"):
        try:
            return float(v)
        except (ValueError, TypeError):
            pass
    m = re.search(r"(\d{1,2})", str(row.get("incentive_detail", "")))
    if m:
        return float(m.group(1))
    return None


def generate_summary() -> str:
    master_count = len(read_csv(MASTER_FINAL))
    new_count = len(read_csv(OUT_NEW))
    total_after = master_count + new_count

    screening = read_csv(OUT_SCREENING)
    screened_count = len(screening)
    ses_count = sum(1 for r in screening if r.get("is_ses_company") == "yes")
    inc_mention = sum(1 for r in screening if r.get("has_incentive_mention") == "yes")
    rates = [_rate_float(r) for r in screening]
    rate_explicit = sum(1 for r in rates if r is not None)
    high_58 = sum(1 for r in rates if r is not None and r >= 58)

    coverage = total_after / POPULATION_ESTIMATE * 100 if POPULATION_ESTIMATE else 0
    gbiz_count = len(read_csv(OUT_9A))
    nta_count = len(read_csv(OUT_9B))

    lines = [
        "# Phase 9 SES企業マスター拡大 サマリー",
        "",
        f"生成日: {today_str()}",
        "",
        "## 概要",
        f"- 既存マスター（Phase 7）: **{master_count}** 社",
        f"- Phase 9A（gBizINFO）取得: **{gbiz_count}** 社",
        f"- Phase 9B（国税庁API）取得: **{nta_count}** 社",
        f"- 新規追加企業（名寄せ後）: **{new_count}** 社",
        f"- 拡張後マスター総数（推定）: **{total_after}** 社",
        f"- 推定母集団（10,000社）に対する網羅率: **{coverage:.1f}%**",
        "",
        "## Bingスクリーニング（Phase 9C・2段階）",
        f"- スクリーニング実施数: **{screened_count}**",
        f"- SES企業と判定: **{ses_count}**",
        f"- インセンティブ言及: **{inc_mention}**",
        f"- 粗利%明示: **{rate_explicit}**",
        f"- 粗利58%以上: **{high_58}**",
        "",
        "## スクリーニング方式",
        "- 第1段階: `\"{会社名}\" SES` でSES企業判定",
        "- 第2段階: SES判定=yes のみ `\"{会社名}\" \"営業\" \"粗利\"` 等でインセンティブ検索",
        "",
        "## 出力ファイル",
        f"- `{OUT_9A.name}`",
        f"- `{OUT_9B.name}`",
        f"- `{OUT_NEW.name}`",
        f"- `{OUT_SCREENING.name}`",
        f"- `{OUT_SUMMARY.name}`",
        "",
        "## APIトークン状況",
        "gBizINFO / 国税庁API のトークン設定手順は `phase9_api_application_guide.md` を参照。",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    summary = generate_summary()
    OUT_SUMMARY.write_text(summary, encoding="utf-8")
    print(summary, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
