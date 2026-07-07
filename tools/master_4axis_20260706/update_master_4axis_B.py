# -*- coding: utf-8 -*-
"""Script B: シミュレーション4シート再計算（2026-07-06）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)

from master_comp_engine import (  # noqa: E402
    MATRIX_HEAD_COUNTS,
    MATRIX_YEARS,
    build_matrix_table,
    compute_team_ordinary,
    format_profit,
    get_gspread_client,
    growth_model_rows,
    matrix_actual_rate,
    matrix_flat_rate,
    salary_simulation_rows,
    update_sheet,
    validate_gates,
)

SS_ID = "1xSmLwXiDrCVPztSnwhEU1SSBpKOInV5Dx63Zg_mKyR4"


def actual_rate_matrix_rows() -> list[list]:
    rows: list[list] = [
        ["営業経常利益（実利率・4軸反映）  2026-07-06確定  単位：万円/年"],
        ["松野岡本粗利込み。役員報酬（松野30万/月）控除前。"],
        [],
    ]
    rows += build_matrix_table(
        "■ 通常メンバーのみ（創業0名）",
        lambda n, y: matrix_actual_rate(n, y, founding_count=0),
    )
    rows += build_matrix_table(
        "■ 全員創業メンバー（軸4+5%込み）",
        lambda n, y: matrix_actual_rate(n, y, founding_count=n),
    )
    rows += build_matrix_table(
        "■ 混合（創業2名＋通常追加）",
        lambda n, y: matrix_actual_rate(n, y, founding_count=min(2, n)),
    )
    return rows


def flat_rate_matrix_rows() -> list[list]:
    rows: list[list] = [
        ["営業経常利益（固定還元率シナリオ）  2026-07-06  単位：万円/年"],
        [],
    ]
    for label, rate in [("65%（下限）", 65), ("75%（一般上限）", 75), ("80%（創業上限）", 80)]:
        rows += build_matrix_table(
            f"還元率 {label}",
            lambda n, y, r=rate: matrix_flat_rate(r, n, y),
        )
    return rows


def main() -> None:
    validate_gates()

    gc = get_gspread_client()
    ss = gc.open_by_key(SS_ID)

    ws1 = ss.worksheet("給与シミュレーション")
    ws1.clear()
    update_sheet(ws1, salary_simulation_rows(), "A1")
    print("[1/4] 給与シミュレーション OK")

    ws2 = ss.worksheet("成長モデル")
    update_sheet(ws2, growth_model_rows(), "A45")
    print("[2/4] 成長モデル OK")

    ws3 = ss.worksheet("経常利益マトリクス")
    ws3.clear()
    update_sheet(ws3, flat_rate_matrix_rows(), "A1")
    print("[3/4] 経常利益マトリクス OK")

    ws4 = ss.worksheet("経常利益（実利率）")
    ws4.clear()
    update_sheet(ws4, actual_rate_matrix_rows(), "A1")
    print("[4/4] 経常利益（実利率） OK")

    ref = compute_team_ordinary(10, 2, scenario_key="262")
    print(f"\n検算: 262・10名・2年目={ref.ordinary_before_exec}万")
    print(f"=== Script B 完了 ===\nhttps://docs.google.com/spreadsheets/d/{SS_ID}/edit")


if __name__ == "__main__":
    main()
