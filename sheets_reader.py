"""
sheets_reader.py
================
Googleスプレッドシートから請求対象人員を読み込む共通モジュール。

書き込み関数 update_to_kado() は execute=True かつ環境変数
SHEETS_WRITE_APPROVED=1（松野承認済み）の両方が必要。
load_active_entries() / scan_nyujomae() は読み取り専用。
"""

from __future__ import annotations

import os
import sys
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from common.date_utils import is_active_in_month
from common.sheet_dates import parse_contract_dates

CREDS_PATH = os.path.join(ROOT, "google_credentials.json")
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

SHEET_CFG = {
    "TERRA": {
        "name_col": 3,
        "status_col": 2,
        "kubun_col": 1,
        "tantou_col": 0,
        "tanka_col": 7,
        "shiire_col": 13,
        "case_col": 6,
        "start_row": 4,
    },
    "フラップテック": {
        "name_col": 2,
        "status_col": 1,
        "kubun_col": None,
        "tantou_col": 0,
        "tanka_col": 6,
        "shiire_col": 7,
        "case_col": 5,
        "start_row": 3,
    },
    "グレイスライン": {
        "name_col": 1,
        "status_col": 0,
        "kubun_col": None,
        "tantou_col": None,
        "tanka_col": 5,
        "shiire_col": 6,
        "case_col": 4,
        "start_row": 3,
    },
}

GL_SITE_FALLBACK = {
    "石崎春光": 30,
    "山内清": 45,
    "荒井大輝": 45,
}

GL_FT_CASE_KEYS = ("グレイスライン", "フラップテック", "GL", "FT")


def ft_tier_rate(active_count: int) -> float:
    """FT稼働件数に応じた粗利率（小坂折半は別途48%固定）。"""
    if active_count <= 10:
        return 0.68
    if active_count <= 13:
        return 0.75
    return 0.80


def _is_gl_ft(case: str) -> bool:
    return any(k in case for k in GL_FT_CASE_KEYS)


def _family_name(name: str) -> str:
    return name.split("(")[0].strip()


def _linked_ft_gl_name(name: str, ft_gl_names: set[str]) -> bool:
    family = _family_name(name)
    if len(family) < 2:
        return False
    return any(_family_name(other).startswith(family) for other in ft_gl_names)


def _collect_ft_gl_active_names(ss) -> set[str]:
    names: set[str] = set()
    for sheet_name in ("フラップテック", "グレイスライン"):
        cfg = SHEET_CFG[sheet_name]
        for row in ss.worksheet(sheet_name).get_all_values()[cfg["start_row"] :]:
            if len(row) <= cfg["name_col"]:
                continue
            status = row[cfg["status_col"]].strip() if cfg["status_col"] < len(row) else ""
            name = row[cfg["name_col"]].strip()
            if "稼働中" in status and _is_name(name):
                names.add(name)
    return names


def _notify_line(text: str) -> None:
    try:
        from line_webhook.line_bridge import push_or_log

        env_path = os.path.join(ROOT, "config", ".env")
        uid = ""
        if os.path.exists(env_path):
            for line in open(env_path, encoding="utf-8"):
                line = line.strip()
                if line.startswith("MATSUNO_LINE_USER_ID="):
                    uid = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if uid:
            push_or_log(uid, text, "sheets_reader")
    except Exception:
        pass


def _gc():
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def _open():
    return _gc().open_by_key(SS_ID)


def _safe_int(v):
    try:
        return int(str(v).replace(",", "").replace("¥", "").strip())
    except Exception:
        return 0


def _is_name(v):
    if not v or str(v).strip() in ("", "None", "氏名", "稼働中合計"):
        return False
    return True


def _normalize_header(cell: str) -> str:
    return str(cell).replace("\n", "").strip()


def _find_header_col(header_rows, col_name):
    if not col_name:
        return None
    target = _normalize_header(col_name)
    for row in header_rows:
        for i, cell in enumerate(row):
            if _normalize_header(cell) == target:
                return i
    return None


def _is_confirmed(val):
    return str(val).strip().upper() in ("TRUE", "1", "〇", "○", "YES", "はい")


def _target_month_str(target_month) -> str | None:
    if target_month is None:
        return None
    if isinstance(target_month, date):
        return f"{target_month.year}-{target_month.month:02d}"
    if hasattr(target_month, "year") and hasattr(target_month, "month"):
        return f"{target_month.year}-{target_month.month:02d}"
    return str(target_month)


def _site_days(raw: str, source: str, name: str) -> int | None:
    days = _safe_int(raw)
    if days > 0:
        return days
    if source == "GL":
        return GL_SITE_FALLBACK.get(name)
    return None


def _terra_entry(row, cfg, *, site_days, profit, kubun, tantou, case, name):
    if kubun == "P":
        if _is_gl_ft(case):
            return None, "GL/FT経由プロパー→TERRA請求除外"
        return {
            "partner": "株式会社TERRA",
            "name": name,
            "profit": profit,
            "seikyu": 15000,
            "rule": "プロパー→15,000円固定",
            "source": "TERRA",
            "kubun": kubun,
            "tantou": tantou,
            "site_days": site_days,
            "is_prop": True,
            "description": "プロパー稼働分",
        }, None
    if kubun == "BP":
        if tantou == "TERRA折半":
            seikyu, rule = int(profit * 0.50), "TERRA折半→粗利×50%"
        elif tantou == "岡本折半":
            seikyu, rule = int(profit * 0.80), "岡本折半→粗利×80%"
        else:
            seikyu, rule = int(profit * 0.80), "BP→粗利×80%"
    else:
        seikyu, rule = 15000, "不明→15,000円固定"
    if seikyu <= 0:
        return None, "請求額0以下"
    return {
        "partner": "株式会社TERRA",
        "name": name,
        "profit": profit,
        "seikyu": seikyu,
        "rule": rule,
        "source": "TERRA",
        "kubun": kubun,
        "tantou": tantou,
        "site_days": site_days,
        "is_prop": False,
        "description": f"{name}様稼働分",
    }, None


def _ft_entry(row, cfg, *, site_days, profit, tantou, name, ft_rate: float = 0.68):
    if tantou == "小坂折半":
        seikyu, rule = int(profit * 0.48), "小坂折半→粗利×48%"
    elif tantou in ("岡本折半", "岡本"):
        pct = int(ft_rate * 100)
        seikyu, rule = int(profit * ft_rate), f"{tantou}→粗利×{pct}%"
    else:
        pct = int(ft_rate * 100)
        seikyu, rule = int(profit * ft_rate), f"通常→粗利×{pct}%"
    if seikyu <= 0:
        return None, "請求額0以下"
    return {
        "partner": "株式会社フラップテック",
        "name": name,
        "profit": profit,
        "seikyu": seikyu,
        "rule": rule,
        "source": "FT",
        "kubun": "",
        "tantou": tantou,
        "site_days": site_days,
        "is_prop": False,
        "description": f"{name}様稼働分",
    }, None


def _gl_entry(row, cfg, *, site_days, profit, name, target_month: date):
    seikyu = int(profit * 0.60)
    if seikyu <= 0:
        return None, "請求額0以下"
    m = target_month.month
    return {
        "partner": "グレイスライン株式会社",
        "name": name,
        "profit": profit,
        "seikyu": seikyu,
        "rule": "GL→粗利×60%",
        "source": "GL",
        "kubun": "",
        "tantou": "",
        "site_days": site_days,
        "is_prop": False,
        "description": f"{name}様{m}月稼働分",
    }, None


def _count_ft_billable_rows(ss, month_date: date | None, kado_col_name: str | None) -> int:
    """フラップテックシート上の請求対象FT稼働件数を数える（階段粗利率用）。"""
    sheet_name = "フラップテック"
    cfg = SHEET_CFG[sheet_name]
    data = ss.worksheet(sheet_name).get_all_values()
    header_rows = data[: cfg["start_row"]]
    kado_col = _find_header_col(header_rows, kado_col_name) if kado_col_name else None
    start_col = _find_header_col(header_rows, "契約開始日")
    end_col = _find_header_col(header_rows, "契約終了日")
    sankaku_col = _find_header_col(header_rows, "参画時期")
    kikan_col = _find_header_col(header_rows, "期間")
    site_col = _find_header_col(header_rows, "支払サイト")
    month_str = month_date.strftime("%Y-%m") if month_date else None
    count = 0

    for row in data[cfg["start_row"] :]:
        if len(row) <= cfg["name_col"]:
            continue
        name = row[cfg["name_col"]].strip()
        status = row[cfg["status_col"]].strip() if cfg["status_col"] < len(row) else ""
        if not _is_name(name) or "稼働中" not in status:
            continue

        start, end = parse_contract_dates(
            row,
            start_col=start_col,
            end_col=end_col,
            sankaku_col=sankaku_col,
            kikan_col=kikan_col,
        )
        if start is None:
            continue

        if kado_col is not None:
            confirmed = row[kado_col].strip() if kado_col < len(row) else ""
            if confirmed:
                if not _is_confirmed(confirmed):
                    continue
            elif month_str and not is_active_in_month(start, end, month_str):
                continue
        elif month_str and not is_active_in_month(start, end, month_str):
            continue

        site_raw = row[site_col].strip() if site_col is not None and site_col < len(row) else ""
        if _site_days(site_raw, "FT", name) is None:
            continue

        tanka = _safe_int(row[cfg["tanka_col"]]) if cfg["tanka_col"] < len(row) else 0
        shiire = _safe_int(row[cfg["shiire_col"]]) if cfg["shiire_col"] < len(row) else 0
        if tanka == 0:
            continue
        if tanka - shiire <= 0:
            continue
        count += 1
    return count


def load_active_entries(target_month=None, *, require_kado=True):
    """稼働確定=TRUE かつ契約期間内の人員を返す。

    Returns:
        (entries, meta)  meta には除外・スキップ理由のリストを含む。
    """
    ss = _open()
    entries = []
    ft_gl_active_names = _collect_ft_gl_active_names(ss)
    excluded_gl_ft_props: list[str] = []
    skipped_no_start: list[str] = []
    skipped_inactive: list[str] = []
    skipped_other: list[str] = []
    site_missing_warnings: list[str] = []

    month_str = _target_month_str(target_month)
    month_date = None
    if month_str:
        y, m = map(int, month_str.split("-"))
        month_date = date(y, m, 1)

    kado_col_name = None
    if month_date is not None:
        kado_col_name = f"{month_date.year}年{month_date.month}月_稼働確定"
    kado_warned = False
    ft_billable_count = _count_ft_billable_rows(ss, month_date, kado_col_name)
    ft_rate = ft_tier_rate(ft_billable_count)

    for sheet_name, source_key, builder in (
        ("TERRA", "TERRA", _terra_entry),
        ("フラップテック", "FT", _ft_entry),
        ("グレイスライン", "GL", _gl_entry),
    ):
        cfg = SHEET_CFG[sheet_name]
        data = ss.worksheet(sheet_name).get_all_values()
        header_rows = data[: cfg["start_row"]]
        kado_col = _find_header_col(header_rows, kado_col_name)
        start_col = _find_header_col(header_rows, "契約開始日")
        end_col = _find_header_col(header_rows, "契約終了日")
        sankaku_col = _find_header_col(header_rows, "参画時期")
        kikan_col = _find_header_col(header_rows, "期間")
        site_col = _find_header_col(header_rows, "支払サイト")

        if kado_col_name and kado_col is None and not kado_warned:
            print(f"[警告] 列 '{kado_col_name}' が見つかりません。全件処理します。")
            kado_warned = True

        for row in data[cfg["start_row"] :]:
            if len(row) <= cfg["name_col"]:
                continue
            name = row[cfg["name_col"]].strip()
            status = row[cfg["status_col"]].strip() if cfg["status_col"] < len(row) else ""
            if not _is_name(name):
                continue
            if "稼働中" not in status:
                continue

            start, end = parse_contract_dates(
                row,
                start_col=start_col,
                end_col=end_col,
                sankaku_col=sankaku_col,
                kikan_col=kikan_col,
            )
            if start is None:
                skipped_no_start.append(f"{sheet_name}/{name}")
                continue

            if kado_col is not None:
                confirmed = row[kado_col].strip() if kado_col < len(row) else ""
                if confirmed:
                    if not _is_confirmed(confirmed):
                        continue
                elif month_str and not is_active_in_month(start, end, month_str):
                    skipped_inactive.append(f"{sheet_name}/{name}")
                    continue
            elif month_str and not is_active_in_month(start, end, month_str):
                skipped_inactive.append(f"{sheet_name}/{name}")
                continue

            case = row[cfg["case_col"]].strip() if cfg["case_col"] < len(row) else ""
            kubun = (
                row[cfg["kubun_col"]].strip()
                if cfg.get("kubun_col") is not None and cfg["kubun_col"] < len(row)
                else ""
            )
            site_raw = row[site_col].strip() if site_col is not None and site_col < len(row) else ""
            site_days = _site_days(site_raw, source_key, name)
            if site_days is None:
                if source_key == "TERRA":
                    gl_ft_via_case = _is_gl_ft(case)
                    gl_ft_via_roster = kubun == "P" and _linked_ft_gl_name(name, ft_gl_active_names)
                    if gl_ft_via_case or gl_ft_via_roster:
                        excluded_gl_ft_props.append(f"{sheet_name}/{name}")
                    else:
                        skipped_other.append(f"{sheet_name}/{name}: 支払サイト未入力（要確認）")
                        warn = f"⚠️ {name}: 支払サイト未入力。請求書に載っていません。"
                        site_missing_warnings.append(warn)
                        _notify_line(warn)
                else:
                    skipped_other.append(f"{sheet_name}/{name}: 支払サイト未入力")
                continue

            tanka = _safe_int(row[cfg["tanka_col"]]) if cfg["tanka_col"] < len(row) else 0
            shiire = _safe_int(row[cfg["shiire_col"]]) if cfg["shiire_col"] < len(row) else 0
            if source_key != "TERRA" and tanka == 0:
                skipped_other.append(f"{sheet_name}/{name}: 単価未入力")
                continue
            profit = tanka - shiire
            if source_key != "TERRA" and profit <= 0:
                skipped_other.append(f"{sheet_name}/{name}: 粗利{profit}円")
                continue

            tantou = (
                row[cfg["tantou_col"]].strip()
                if cfg.get("tantou_col") is not None and cfg["tantou_col"] < len(row)
                else ""
            )

            if source_key == "TERRA":
                entry, reason = builder(
                    row, cfg, site_days=site_days, profit=profit, kubun=kubun, tantou=tantou, case=case, name=name
                )
            elif source_key == "FT":
                entry, reason = builder(
                    row, cfg, site_days=site_days, profit=profit, tantou=tantou, name=name, ft_rate=ft_rate
                )
            else:
                entry, reason = builder(
                    row, cfg, site_days=site_days, profit=profit, name=name, target_month=month_date
                )

            if entry is None:
                if reason and "GL/FT経由" in reason:
                    excluded_gl_ft_props.append(f"{sheet_name}/{name}")
                else:
                    skipped_other.append(f"{sheet_name}/{name}: {reason}")
                continue
            entries.append(entry)

    meta = {
        "excluded_gl_ft_props": excluded_gl_ft_props,
        "skipped_no_start": skipped_no_start,
        "skipped_inactive": skipped_inactive,
        "skipped_other": skipped_other,
        "site_missing_warnings": site_missing_warnings,
    }
    return entries, meta


def scan_nyujomae():
    ss = _open()
    targets = []
    sheet_scan = {
        "TERRA": {"name_col": 3, "status_col": 2, "start_row": 4},
        "フラップテック": {"name_col": 2, "status_col": 1, "start_row": 3},
        "グレイスライン": {"name_col": 1, "status_col": 0, "start_row": 3},
    }
    for sname, cfg in sheet_scan.items():
        data = ss.worksheet(sname).get_all_values()
        for row in data[cfg["start_row"] :]:
            if len(row) <= cfg["name_col"]:
                continue
            status = row[cfg["status_col"]].strip()
            name = row[cfg["name_col"]].strip()
            if status == "入場前" and _is_name(name):
                targets.append({"sheet": sname, "name": name})
    return targets


def update_to_kado(targets, execute=False):
    """入場前→稼働中 更新。execute=True かつ SHEETS_WRITE_APPROVED=1 のみ書き込み。"""
    if not targets:
        return []
    if not execute:
        print("[update_to_kado] execute=False のため書き込みをスキップ（人間確認ゲート）")
        return []
    if os.environ.get("SHEETS_WRITE_APPROVED", "").strip() != "1":
        print("[update_to_kado] SHEETS_WRITE_APPROVED=1 未設定のため書き込み拒否（松野承認必須）")
        return []
    ss = _open()
    sheet_scan = {
        "TERRA": {"name_col": 3, "status_col": 2, "start_row": 4},
        "フラップテック": {"name_col": 2, "status_col": 1, "start_row": 3},
        "グレイスライン": {"name_col": 1, "status_col": 0, "start_row": 3},
    }
    updated = []
    for t in targets:
        cfg = sheet_scan[t["sheet"]]
        ws = ss.worksheet(t["sheet"])
        data = ws.get_all_values()
        for i, row in enumerate(data[cfg["start_row"] :], start=cfg["start_row"] + 1):
            if len(row) <= cfg["name_col"]:
                continue
            if row[cfg["name_col"]].strip() == t["name"] and row[cfg["status_col"]].strip() == "入場前":
                ws.update_cell(i + 1, cfg["status_col"] + 1, "稼働中")
                updated.append(f"[{t['sheet']}] {t['name']}: 入場前 → 稼働中")
                break
    return updated


if __name__ == "__main__":
    print("=== 稼働中人員確認 ===")
    entries, meta = load_active_entries()
    for e in entries:
        print(f"  {e['source']} | {e['name']} | 粗利{e['profit']:,} | 請求{e['seikyu']:,} | {e['rule']}")
    print(f"\n合計: {len(entries)}名")
