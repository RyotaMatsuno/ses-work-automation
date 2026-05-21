
"""
sheets_reader.py
================
Googleスプレッドシートから稼働中人員を読み込む共通モジュール。
freee_invoice_v2.py / auto_invoice_and_update.py から import して使う。

Excel版のload_active_entries() / scan_nyujomae() / update_to_kado() を
Sheetsで完全置き換え。
"""
import gspread
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID      = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES     = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

def _gc():
    creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)

def _open():
    return _gc().open_by_key(SS_ID)

# --- シート別カラム定義（0-indexed） ---
SHEET_CFG = {
    "TERRA":         {"name_col": 3, "status_col": 2, "kubun_col": 1, "tantou_col": 0,
                      "tanka_col": 7, "shiire_col": 13, "case_col": 6, "start_row": 4},
    "フラップテック": {"name_col": 2, "status_col": 1, "kubun_col": None, "tantou_col": 0,
                      "tanka_col": 6, "shiire_col": 7, "case_col": 5, "start_row": 3},
    "グレイスライン": {"name_col": 1, "status_col": 0, "kubun_col": None, "tantou_col": None,
                      "tanka_col": 5, "shiire_col": 6, "case_col": 4, "start_row": 3},
}

def _safe_int(v):
    try:
        return int(str(v).replace(",", "").replace("¥", "").strip())
    except:
        return 0

def _is_name(v):
    if not v or str(v).strip() in ("", "None", "氏名", "稼働中合計"):
        return False
    return True


# ===== 稼働中人員取得（freee請求書用）=====
def load_active_entries():
    ss = _open()
    entries = []

    # --- TERRA ---
    cfg = SHEET_CFG["TERRA"]
    data = ss.worksheet("TERRA").get_all_values()
    for row in data[cfg["start_row"]:]:
        if len(row) <= cfg["name_col"]: continue
        tantou = row[cfg["tantou_col"]].strip()
        kubun  = row[cfg["kubun_col"]].strip()
        status = row[cfg["status_col"]].strip()
        name   = row[cfg["name_col"]].strip()
        case   = row[cfg["case_col"]].strip() if cfg["case_col"] < len(row) else ""
        tanka  = _safe_int(row[cfg["tanka_col"]])  if cfg["tanka_col"] < len(row) else 0
        shiire = _safe_int(row[cfg["shiire_col"]]) if cfg["shiire_col"] < len(row) else 0

        if "稼働中" not in status or not _is_name(name): continue

        is_gl_ft = any(k in case for k in ["グレイスライン", "フラップテック", "GL", "FT"])
        profit = tanka - shiire

        if kubun == "P":
            if is_gl_ft: continue
            seikyu, rule = 15000, "プロパー→15,000円固定"
        elif kubun == "BP":
            if tantou == "TERRA折半":
                seikyu, rule = int(profit * 0.50), "TERRA折半→粗利×50%"
            elif tantou in ("岡本折半", "小坂折半"):
                seikyu, rule = int(profit * 0.80), f"{tantou}→粗利×80%"
            else:
                seikyu, rule = int(profit * 0.80), "BP→粗利×80%"
        else:
            seikyu, rule = 15000, "不明→15,000円固定"

        if seikyu <= 0: continue
        entries.append({"partner":"株式会社TERRA","name":name,"profit":profit,"seikyu":seikyu,"rule":rule,"source":"TERRA"})

    # --- フラップテック ---
    cfg = SHEET_CFG["フラップテック"]
    data = ss.worksheet("フラップテック").get_all_values()
    for row in data[cfg["start_row"]:]:
        if len(row) <= cfg["name_col"]: continue
        tantou = row[cfg["tantou_col"]].strip()
        status = row[cfg["status_col"]].strip()
        name   = row[cfg["name_col"]].strip()
        tanka  = _safe_int(row[cfg["tanka_col"]])  if cfg["tanka_col"] < len(row) else 0
        shiire = _safe_int(row[cfg["shiire_col"]]) if cfg["shiire_col"] < len(row) else 0

        if "稼働中" not in status or not _is_name(name): continue
        if tanka == 0: continue
        profit = tanka - shiire
        if profit <= 0: continue

        if tantou == "小坂折半":
            seikyu, rule = int(profit * 0.48), "小坂折半→粗利×48%"
        elif tantou == "岡本新営業":
            seikyu, rule = int(profit * 0.68), "岡本新営業→粗利×68%（払出20%）"
        elif tantou in ("岡本折半","岡本"):
            seikyu, rule = int(profit * 0.68), f"{tantou}→粗利×68%"
        else:
            seikyu, rule = int(profit * 0.68), "通常→粗利×68%"

        if seikyu <= 0: continue
        entries.append({"partner":"株式会社フラップテック","name":name,"profit":profit,"seikyu":seikyu,"rule":rule,"source":"FT"})

    # --- グレイスライン ---
    cfg = SHEET_CFG["グレイスライン"]
    data = ss.worksheet("グレイスライン").get_all_values()
    for row in data[cfg["start_row"]:]:
        if len(row) <= cfg["name_col"]: continue
        status = row[cfg["status_col"]].strip()
        name   = row[cfg["name_col"]].strip()
        tanka  = _safe_int(row[cfg["tanka_col"]])  if cfg["tanka_col"] < len(row) else 0
        shiire = _safe_int(row[cfg["shiire_col"]]) if cfg["shiire_col"] < len(row) else 0

        if "稼働中" not in status or not _is_name(name): continue
        if tanka == 0: continue
        profit = tanka - shiire
        if profit <= 0: continue

        seikyu = int(profit * 0.60)
        if seikyu <= 0: continue
        entries.append({"partner":"グレイスライン株式会社","name":name,"profit":profit,"seikyu":seikyu,"rule":"GL→粗利×60%","source":"GL"})

    return entries


# ===== 入場前スキャン =====
def scan_nyujomae():
    ss = _open()
    targets = []
    sheet_scan = {
        "TERRA":         {"name_col": 3, "status_col": 2, "start_row": 4},
        "フラップテック": {"name_col": 2, "status_col": 1, "start_row": 3},
        "グレイスライン": {"name_col": 1, "status_col": 0, "start_row": 3},
    }
    for sname, cfg in sheet_scan.items():
        data = ss.worksheet(sname).get_all_values()
        for row in data[cfg["start_row"]:]:
            if len(row) <= cfg["name_col"]: continue
            status = row[cfg["status_col"]].strip()
            name   = row[cfg["name_col"]].strip()
            if status == "入場前" and _is_name(name):
                targets.append({"sheet": sname, "name": name})
    return targets


# ===== 入場前→稼働中 更新 =====
def update_to_kado(targets):
    if not targets: return []
    ss = _open()
    sheet_scan = {
        "TERRA":         {"name_col": 3, "status_col": 2, "start_row": 4},
        "フラップテック": {"name_col": 2, "status_col": 1, "start_row": 3},
        "グレイスライン": {"name_col": 1, "status_col": 0, "start_row": 3},
    }
    updated = []
    for t in targets:
        cfg = sheet_scan[t["sheet"]]
        ws = ss.worksheet(t["sheet"])
        data = ws.get_all_values()
        for i, row in enumerate(data[cfg["start_row"]:], start=cfg["start_row"]+1):
            if len(row) <= cfg["name_col"]: continue
            if row[cfg["name_col"]].strip() == t["name"] and row[cfg["status_col"]].strip() == "入場前":
                # gspreadのrow/col は1-indexed
                ws.update_cell(i+1, cfg["status_col"]+1, "稼働中")
                updated.append(f"[{t['sheet']}] {t['name']}: 入場前 → 稼働中")
                break
    return updated


if __name__ == "__main__":
    print("=== 稼働中人員確認 ===")
    entries = load_active_entries()
    for e in entries:
        print(f"  {e['source']} | {e['name']} | 粗利{e['profit']:,} | 請求{e['seikyu']:,} | {e['rule']}")
    print(f"\n合計: {len(entries)}名")
    print("\n=== 入場前スキャン ===")
    nyujomae = scan_nyujomae()
    print(f"  {len(nyujomae)}名: {nyujomae}")
