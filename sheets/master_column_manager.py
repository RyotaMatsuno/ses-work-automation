#!/usr/bin/env python3
"""契約マスターSpreadsheetへの月次列追加・稼働確定値セット（契約開始日/終了日ベース）。"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials as ServiceAccountCredentials

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
SHEETS_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common.date_utils import is_active_in_month
from common.sheet_dates import parse_contract_dates

SPREADSHEET_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SERVICE_ACCOUNT_PATH = ROOT_DIR / "google_credentials.json"
GSPREAD_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

SHEET_TABS = ("TERRA", "フラップテック", "グレイスライン")
SHEET_CFG = {
    "TERRA": {"header_rows": 4, "name_col": 3, "status_col": 2},
    "フラップテック": {"header_rows": 3, "name_col": 2, "status_col": 1},
    "グレイスライン": {"header_rows": 3, "name_col": 1, "status_col": 0},
}
KEIYAKU_KUBUN = "契約区分"
TERRA_KUBUN_CLEAR_VALUE = "業務委託料"

WRITE_PATH_FUNCTIONS = (
    "_append_column_at",
    "_write_cells",
    "add_monthly_column",
    "populate_active_status",
    "clear_terra_kubun",
)

logger = logging.getLogger("master_column_manager")


@dataclass
class PersonRow:
    sheet: str
    row_index: int
    name: str
    start: Any
    end: Any


def _load_env() -> dict[str, str]:
    env_path = ROOT_DIR / "config" / ".env"
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _notify_matsuno(text: str) -> None:
    try:
        from line_webhook.line_bridge import push_or_log

        uid = _load_env().get("MATSUNO_LINE_USER_ID", "")
        if uid:
            push_or_log(uid, text, "master_column_manager")
    except Exception as exc:
        logger.error("LINE通知失敗: %s", exc)


def _guard_write(execute: bool, caller: str) -> bool:
    if not execute:
        logger.info("[%s] dry-run: 書き込みブロック", caller)
        return False
    if os.environ.get("SHEETS_WRITE_APPROVED", "").strip() != "1":
        logger.warning("[%s] SHEETS_WRITE_APPROVED=1 未設定: 書き込みブロック", caller)
        return False
    return True


def get_sheets_service():
    creds = ServiceAccountCredentials.from_service_account_file(str(SERVICE_ACCOUNT_PATH), scopes=GSPREAD_SCOPES)
    return gspread.authorize(creds).open_by_key(SPREADSHEET_ID)


def _retry(label: str, fn, retries: int = 3):
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            wait = 2**attempt
            logger.warning("%s 失敗 attempt=%s/%s: %s", label, attempt + 1, retries, exc)
            time.sleep(wait)
    msg = f"[master_column_manager] {label} が{retries}回失敗: {last_exc}"
    _notify_matsuno(msg)
    raise RuntimeError(msg) from last_exc


def parse_target_month(target_month: str) -> tuple[int, int]:
    y, m = map(int, target_month.split("-"))
    return y, m


def kado_column_name(year: int, month: int) -> str:
    return f"{year}年{month}月_稼働確定"


def _find_col(header_rows: list[list[str]], col_name: str) -> int | None:
    target = col_name.replace("\n", "").strip()
    for row in header_rows:
        for i, cell in enumerate(row):
            if str(cell).replace("\n", "").strip() == target:
                return i
    return None


def _read_sheet(spreadsheet, tab: str) -> list[list[str]]:
    return spreadsheet.worksheet(tab).get_all_values()


def _append_column_at(
    spreadsheet,
    tab: str,
    col_name: str,
    insert_at_0based: int,
    *,
    execute: bool,
) -> bool:
    if not _guard_write(execute, f"_append_column_at/{tab}/{col_name}"):
        return False

    data = _read_sheet(spreadsheet, tab)
    cfg = SHEET_CFG[tab]
    header_rows = data[: cfg["header_rows"]]
    if _find_col(header_rows, col_name) is not None:
        return False

    ws = spreadsheet.worksheet(tab)
    sheet_id = ws.id

    def _insert():
        spreadsheet.batch_update(
            {
                "requests": [
                    {
                        "insertDimension": {
                            "range": {
                                "sheetId": sheet_id,
                                "dimension": "COLUMNS",
                                "startIndex": insert_at_0based,
                                "endIndex": insert_at_0based + 1,
                            },
                            "inheritFromBefore": True,
                        }
                    }
                ]
            }
        )
        ws.update_cell(cfg["header_rows"], insert_at_0based + 1, col_name)

    _retry(f"append column {tab}/{col_name}", _insert)
    logger.info("列追加: %s / %s (index=%s)", tab, col_name, insert_at_0based)
    return True


def _append_column_end(spreadsheet, tab: str, col_name: str, *, execute: bool) -> bool:
    data = _read_sheet(spreadsheet, tab)
    width = max((len(r) for r in data), default=0)
    return _append_column_at(spreadsheet, tab, col_name, width, execute=execute)


def _write_cells(spreadsheet, writes: list[tuple[str, int, int, str]], *, execute: bool, label: str) -> int:
    if not writes:
        return 0
    if not _guard_write(execute, label):
        return 0

    def _do():
        for tab, row, col, value in writes:
            spreadsheet.worksheet(tab).update_cell(row, col, value)

    _retry(label, _do)
    return len(writes)


def add_monthly_column(target_month: str, *, execute: bool = False) -> bool:
    year, month = parse_target_month(target_month)
    col_name = kado_column_name(year, month)
    spreadsheet = get_sheets_service()
    would_add = False
    for tab in SHEET_TABS:
        data = _read_sheet(spreadsheet, tab)
        header_rows = data[: SHEET_CFG[tab]["header_rows"]]
        if _find_col(header_rows, col_name) is None:
            would_add = True
            _append_column_end(spreadsheet, tab, col_name, execute=execute)
    return would_add


def ensure_notion_name_column(*, execute: bool = False) -> bool:
    """廃止（non-op）。"""
    return False


def ensure_keiyaku_kubun_column(*, execute: bool = False) -> bool:
    """廃止（non-op）。"""
    return False


def _collect_person_rows(spreadsheet) -> list[PersonRow]:
    people: list[PersonRow] = []
    for tab in SHEET_TABS:
        data = _read_sheet(spreadsheet, tab)
        cfg = SHEET_CFG[tab]
        header_rows = data[: cfg["header_rows"]]
        start_col = _find_col(header_rows, "契約開始日")
        end_col = _find_col(header_rows, "契約終了日")
        sankaku_col = _find_col(header_rows, "参画時期")
        kikan_col = _find_col(header_rows, "期間")

        for row_idx in range(cfg["header_rows"], len(data)):
            row = data[row_idx]
            name = row[cfg["name_col"]].strip() if cfg["name_col"] < len(row) else ""
            if not name or name in ("氏名", "稼働中合計"):
                continue
            start, end = parse_contract_dates(
                row,
                start_col=start_col,
                end_col=end_col,
                sankaku_col=sankaku_col,
                kikan_col=kikan_col,
            )
            people.append(PersonRow(sheet=tab, row_index=row_idx + 1, name=name, start=start, end=end))
    return people


def populate_active_status(target_month: str, *, execute: bool = False) -> dict[str, Any]:
    """Sheet の契約開始日・契約終了日のみで稼働判定（Notion不使用）。"""
    year, month = parse_target_month(target_month)
    col_name = kado_column_name(year, month)
    spreadsheet = get_sheets_service()
    people = _collect_person_rows(spreadsheet)

    results: list[dict[str, Any]] = []
    counts = {"TRUE": 0, "FALSE": 0, "skip": 0}
    skipped_no_start: list[str] = []

    for person in people:
        if person.start is None:
            counts["skip"] += 1
            skipped_no_start.append(f"{person.sheet}/{person.name}（行{person.row_index}）")
            value = ""
        else:
            value = "TRUE" if is_active_in_month(person.start, person.end, target_month) else "FALSE"
            counts[value] += 1
        results.append(
            {
                "tab": person.sheet,
                "name": person.name,
                "row_num": person.row_index,
                "start": str(person.start) if person.start else "",
                "end": str(person.end) if person.end else "",
                "value": value,
            }
        )

    summary = {
        "target_month": target_month,
        "column": col_name,
        "counts": counts,
        "skipped_no_start": skipped_no_start,
        "results": results,
    }

    print(f"=== populate_active_status / {target_month} ===")
    print(f"列名: {col_name}")
    print(f"TRUE={counts['TRUE']} FALSE={counts['FALSE']} スキップ(開始日なし)={counts['skip']}")
    print("判定結果:")
    for r in results:
        if r["value"]:
            print(f"  {r['tab']}: {r['name']}（行{r['row_num']}）→ {r['value']}")
        elif r["name"]:
            print(f"  {r['tab']}: {r['name']}（行{r['row_num']}）→ スキップ（開始日なし）")
    if skipped_no_start:
        print("開始日未入力:")
        for item in skipped_no_start:
            print(f"  - {item}")

    if not execute:
        print("DRY-RUN: Sheet書き込みなし")
        return summary

    if not _guard_write(execute, "populate_active_status"):
        return summary

    data_by_tab = {tab: _read_sheet(spreadsheet, tab) for tab in SHEET_TABS}
    writes: list[tuple[str, int, int, str]] = []
    for person, result in zip(people, results):
        if not result["value"]:
            continue
        cfg = SHEET_CFG[person.sheet]
        header_rows = data_by_tab[person.sheet][: cfg["header_rows"]]
        col_idx = _find_col(header_rows, col_name)
        if col_idx is None:
            raise RuntimeError(f"{person.sheet}: 列 {col_name} が見つかりません")
        writes.append((person.sheet, person.row_index, col_idx + 1, result["value"]))

    n = _write_cells(spreadsheet, writes, execute=True, label="稼働確定値書込")
    print(f"書き込み完了: {n} セル")
    return summary


def clear_terra_kubun(*, execute: bool = False) -> dict[str, Any]:
    """TERRAタブの契約区分「業務委託料」を空欄に戻す。"""
    spreadsheet = get_sheets_service()
    data = _read_sheet(spreadsheet, "TERRA")
    cfg = SHEET_CFG["TERRA"]
    header_rows = data[: cfg["header_rows"]]
    col_idx = _find_col(header_rows, KEIYAKU_KUBUN)
    if col_idx is None:
        print("契約区分列が見つかりません")
        return {"before": 0, "cleared": 0}

    targets: list[tuple[int, str]] = []
    for row_idx in range(cfg["header_rows"], len(data)):
        row = data[row_idx]
        name = row[cfg["name_col"]].strip() if cfg["name_col"] < len(row) else ""
        if not name or name in ("氏名", "稼働中合計"):
            continue
        val = row[col_idx].strip() if col_idx < len(row) else ""
        if val == TERRA_KUBUN_CLEAR_VALUE:
            targets.append((row_idx + 1, name))

    print(f"=== clear-terra-kubun / {'EXECUTE' if execute else 'DRY-RUN'} ===")
    print(f"クリア対象: {len(targets)}件（値='{TERRA_KUBUN_CLEAR_VALUE}'）")
    for row_num, name in targets:
        print(f"  行{row_num}: {name}")

    writes = [("TERRA", row_num, col_idx + 1, "") for row_num, _ in targets]
    if execute:
        n = _write_cells(spreadsheet, writes, execute=True, label="clear_terra_kubun")
        print(f"クリア完了: {n} セル")
    else:
        print("DRY-RUN: 書き込みなし")

    return {"before": len(targets), "cleared": len(targets) if execute else 0}


def check_state(target_month: str | None = None) -> None:
    spreadsheet = get_sheets_service()
    year, month = parse_target_month(target_month) if target_month else (2026, 7)
    kado_col = kado_column_name(year, month)

    print(f"=== check-state / spreadsheet={SPREADSHEET_ID} ===")
    for tab in SHEET_TABS:
        data = _read_sheet(spreadsheet, tab)
        cfg = SHEET_CFG[tab]
        header_rows = data[: cfg["header_rows"]]
        headers = header_rows[-1] if header_rows else []
        print(f"\n--- {tab} ---")
        print(f"最終ヘッダー: {headers}")
        for col_name in (kado_col, KEIYAKU_KUBUN):
            idx = _find_col(header_rows, col_name)
            print(f"  列「{col_name}」: {'あり index=' + str(idx) if idx is not None else 'なし'}")
            if idx is not None:
                filled = empty = 0
                for row in data[cfg["header_rows"] :]:
                    if cfg["name_col"] >= len(row):
                        continue
                    name = row[cfg["name_col"]].strip()
                    if not name or name in ("氏名", "稼働中合計"):
                        continue
                    val = row[idx].strip() if idx < len(row) else ""
                    if val:
                        filled += 1
                    else:
                        empty += 1
                print(f"    データ行: 値あり={filled} 空欄={empty}")


def run(target_month: str, *, execute: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print(f"=== master_column_manager / {'EXECUTE' if execute else 'DRY-RUN'} ===")
    if execute and not _guard_write(True, "run"):
        raise RuntimeError("--execute には SHEETS_WRITE_APPROVED=1（松野承認）が必要です")

    added = add_monthly_column(target_month, execute=execute)
    print(f"月次列追加: {'追加' if added and execute else '追加予定' if added else '既存（スキップ）'}")
    populate_active_status(target_month, execute=execute)


def main() -> None:
    parser = argparse.ArgumentParser(description="契約マスター列自動追加")
    parser.add_argument("target_month", nargs="?", help="対象月 YYYY-MM または clear-terra-kubun")
    parser.add_argument("--dry-run", action="store_true", help="Sheet書き込みなし（デフォルト）")
    parser.add_argument("--execute", action="store_true", help="Sheetへ実書き込み（SHEETS_WRITE_APPROVED=1 必須）")
    parser.add_argument("--check-state", action="store_true", help="Sheet列状態をdump")
    args = parser.parse_args()

    if args.check_state:
        check_state(args.target_month if args.target_month and args.target_month != "clear-terra-kubun" else None)
        return

    if args.target_month == "clear-terra-kubun":
        clear_terra_kubun(execute=args.execute)
        return

    if not args.target_month:
        parser.error("target_month が必要です（例: 2026-07 または clear-terra-kubun）")
    run(args.target_month, execute=args.execute)


if __name__ == "__main__":
    main()
