"""
請求書作成後ステータス自動更新スクリプト
使い方: python update_status_on_invoice.py <氏名1> [<氏名2> ...]
例: python update_status_on_invoice.py "川崎健太" "橋本奈緒"

機能:
- 指定した人員のステータスを「入場前」→「稼働中」に更新
- TERRA/フラップテック/グレイスライン 全シートを対象
- バックアップ自動作成
"""

import shutil
import sys
from datetime import datetime

import openpyxl

EXCEL_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"


def update_status(names: list[str]):
    bak = EXCEL_PATH.replace(".xlsx", f"_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    shutil.copy2(EXCEL_PATH, bak)
    print(f"バックアップ: {bak}")

    wb = openpyxl.load_workbook(EXCEL_PATH)
    changes = []
    not_found = []

    # シート別の氏名列・ステータス列の定義
    sheet_configs = {
        "TERRA": {"name_col": 4, "status_col": 3, "start_row": 5},
        "フラップテック": {"name_col": 3, "status_col": 2, "start_row": 4},
        "グレイスライン": {"name_col": 2, "status_col": 1, "start_row": 4},
    }

    for name in names:
        found = False
        for sheet_name, cfg in sheet_configs.items():
            ws = wb[sheet_name]
            nc = cfg["name_col"] - 1
            sc = cfg["status_col"] - 1
            for row in ws.iter_rows(min_row=cfg["start_row"], values_only=False):
                cell_name = row[nc].value
                cell_status = row[sc].value
                if cell_name == name:
                    found = True
                    if cell_status == "入場前":
                        row[sc].value = "稼働中"
                        changes.append(f"[{sheet_name}] {name}: 入場前 → 稼働中")
                    else:
                        changes.append(f"[{sheet_name}] {name}: ステータス={cell_status}（変更不要or既に稼働中）")
        if not found:
            not_found.append(name)

    wb.save(EXCEL_PATH)

    if changes:
        print("変更:")
        for c in changes:
            print(f"  {c}")
    if not_found:
        print("未発見（名前確認要）:")
        for n in not_found:
            print(f"  {n}")
    print("保存完了")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python update_status_on_invoice.py <氏名1> [<氏名2> ...]")
        sys.exit(1)
    names = sys.argv[1:]
    update_status(names)
