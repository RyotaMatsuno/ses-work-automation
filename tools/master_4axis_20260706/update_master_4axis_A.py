# -*- coding: utf-8 -*-
"""Script A: 前提条件 / 営業報酬4軸 / 確定事項一覧 更新（2026-07-06）。"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import os

_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BASE)

from master_comp_engine import (  # noqa: E402
    axis_sheet_rows,
    confirmed_items_rows,
    get_gspread_client,
    premise_patch_rows,
    update_sheet,
)

SS_ID = "1xSmLwXiDrCVPztSnwhEU1SSBpKOInV5Dx63Zg_mKyR4"


def main() -> None:
    gc = get_gspread_client()
    ss = gc.open_by_key(SS_ID)

    ws1 = ss.worksheet("前提条件")
    update_sheet(ws1, premise_patch_rows(), "A54")
    print("[1/3] 前提条件: 2026-07-06追記 OK")

    ws2 = ss.worksheet("営業報酬4軸")
    update_sheet(ws2, axis_sheet_rows(), "A1")
    print("[2/3] 営業報酬4軸: 全面更新 OK")

    ws3 = ss.worksheet("確定事項一覧")
    update_sheet(ws3, confirmed_items_rows(), "A52")
    print("[3/3] 確定事項一覧: 5件追記 OK")

    print(f"\n=== Script A 完了 ===\nhttps://docs.google.com/spreadsheets/d/{SS_ID}/edit")


if __name__ == "__main__":
    main()
