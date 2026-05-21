"""
freee_invoice_v2.py
契約マスターExcelを正として稼働中人員の請求書をfreeeにドラフト作成。

請求ルール:
【TERRA】
  P（プロパー）: GL/FP経由以外 → 15,000円/人（税別）固定
  P（プロパー）: GL/FP経由稼働 → 請求なし
  BP: 粗利×80%
  TERRA折半: 粗利×50%
  岡本折半: 粗利×80%
【フラップテック】
  通常: 粗利×68%
  小坂折半: 粗利×48%
  岡本折半: 粗利×68%
  岡本: 粗利×68%全額払出
【グレイスライン】
  粗利×60%
"""

import os, sys, requests
from datetime import date
from dateutil.relativedelta import relativedelta
import openpyxl

# token_managerを参照（自動リフレッシュ付き）
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
from token_manager import get_headers

# ===== 設定 =====
EXCEL_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
FREEE_BASE = "https://api.freee.co.jp/api/1"
COMPANY_ID = 11712776

def freee_headers():
    h = get_headers()
    h["Content-Type"] = "application/json"
    return h

def safe_int(v):
    """値を安全にintに変換。文字列や日付型はスキップ(0返却)"""
    if v is None:
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    # 文字列・日付型はスキップ
    return 0

def is_valid_name(v):
    """氏名として有効かチェック。日付型・数値・空は除外"""
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return False
    import datetime
    if isinstance(v, (datetime.datetime, datetime.date)):
        return False
    s = str(v).strip()
    if not s or s in ("NaN", "稼働中合計"):
        return False
    # 数字だけの文字列も除外
    if s.replace("/", "").replace("-", "").isdigit():
        return False
    return True

# ===== Excel読み込み =====
def load_active_entries():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    entries = []

    # --- TERRA ---
    # ヘッダー: 担当(0) 区分(1) ステータス(2) 氏名(3) ... 案件/上位会社(6) 単価(案件)(7) ... 仕入単価(12)
    ws = wb["TERRA"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "担当" in str(row[0]):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            tantou   = str(row[0] or "").strip()
            kubun    = str(row[1] or "").strip()
            status   = str(row[2] or "").strip()
            name     = row[3]
            case     = str(row[6] or "").strip()
            tanka    = safe_int(row[7])
            shiire   = safe_int(row[12])

            if "稼働中" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()

            is_gl_ft = any(k in case for k in ["グレイスライン", "フラップテック", "GL", "FT"])
            profit = tanka - shiire

            if kubun == "P":
                if is_gl_ft:
                    continue  # 請求なし
                seikyu = 15000
                rule   = "プロパー→15,000円固定"
            elif kubun == "BP":
                if tantou == "TERRA折半":
                    seikyu = int(profit * 0.50)
                    rule   = "TERRA折半→粗利×50%"
                elif tantou == "岡本折半":
                    seikyu = int(profit * 0.80)
                    rule   = "岡本折半→粗利×80%（岡本払出あり）"
                else:
                    seikyu = int(profit * 0.80)
                    rule   = "BP→粗利×80%"
            else:
                seikyu = 15000
                rule   = "不明→15,000円固定"

            if seikyu <= 0: continue

            entries.append({
                "partner": "株式会社TERRA",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": rule, "source": "TERRA"
            })

    # --- フラップテック ---
    # ヘッダー: 担当(0) ステータス(1) 氏名(2) 参画時期(3) 期間(4) 案件/上位(5) 案件単価(6) 仕入単価(7)
    ws = wb["フラップテック"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "担当" in str(row[0]) and "ステータス" in str(row[1] or ""):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            tantou  = str(row[0] or "").strip()
            status  = str(row[1] or "").strip()
            name    = row[2]
            tanka   = safe_int(row[6])   # 案件単価(上位から)
            shiire  = safe_int(row[7])   # 仕入単価(下位へ)

            if "稼働中" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()
            if tanka == 0: continue  # 単価未入力はスキップ

            profit = tanka - shiire

            if profit <= 0:
                print(f"  [SKIP] {name}: 粗利{profit:,}円（単価={tanka:,} 仕入={shiire:,}）")
                continue

            if tantou == "小坂折半":
                seikyu = int(profit * 0.48)
                rule   = "小坂折半→粗利×48%"
            elif tantou in ("岡本折半", "岡本"):
                seikyu = int(profit * 0.68)
                rule   = f"{tantou}→粗利×68%（岡本払出あり）"
            else:
                seikyu = int(profit * 0.68)
                rule   = "通常→粗利×68%"

            if seikyu <= 0: continue

            entries.append({
                "partner": "株式会社フラップテック",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": rule, "source": "FT"
            })

    # --- グレイスライン ---
    # ヘッダー: ステータス(0) 氏名(1) 参画時期(2) 期間(3) 案件/上位(4) 案件単価(5) 仕入単価(6)
    ws = wb["グレイスライン"]
    rows = list(ws.iter_rows(values_only=True))
    header_row = None
    for i, row in enumerate(rows):
        if row and "ステータス" in str(row[0]):
            header_row = i
            break
    if header_row is not None:
        for row in rows[header_row+1:]:
            if not any(row): continue
            status  = str(row[0] or "").strip()
            name    = row[1]
            tanka   = safe_int(row[5])   # 案件単価(上位から)
            shiire  = safe_int(row[6])   # 仕入単価(下位へ)

            if "稼働中" not in status: continue
            if not is_valid_name(name): continue
            name = str(name).strip()
            if tanka == 0: continue

            profit = tanka - shiire

            if profit <= 0:
                print(f"  [SKIP] {name}: 粗利{profit:,}円（単価={tanka:,} 仕入={shiire:,}）")
                continue

            seikyu = int(profit * 0.60)
            if seikyu <= 0: continue

            entries.append({
                "partner": "グレイスライン株式会社",
                "name": name, "profit": profit, "seikyu": seikyu,
                "rule": "GL→粗利×60%", "source": "GL"
            })

    return entries

# ===== freee: 取引先取得/作成 =====
def get_or_create_partner(name):
    res = requests.get(f"{FREEE_BASE}/partners",
        headers=freee_headers(),
        params={"company_id": COMPANY_ID, "keyword": name})
    partners = res.json().get("partners", [])
    if partners: return partners[0]["id"]
    res2 = requests.post(f"{FREEE_BASE}/partners",
        headers=freee_headers(),
        json={"company_id": COMPANY_ID, "name": name, "partner_type": "customer"})
    return res2.json()["partner"]["id"]

# ===== freee: 請求書ドラフト作成 =====
def create_invoice(entry, issue_date, due_date):
    partner_id = get_or_create_partner(entry["partner"])
    mon = f"{issue_date.year}年{issue_date.month}月"
    payload = {
        "company_id": COMPANY_ID,
        "issue_date":  issue_date.strftime("%Y-%m-%d"),
        "due_date":    due_date.strftime("%Y-%m-%d"),
        "partner_id":  partner_id,
        "invoice_status": "draft",
        "title": f"{mon}分 業務委託料（{entry['name']}様）",
        "description": f"[{entry['rule']}] 粗利: {entry['profit']:,}円",
        "invoice_lines": [{
            "name":       f"業務委託料（{entry['name']}様）{mon}分",
            "quantity":   1,
            "unit_price": entry["seikyu"],
            "tax_code":   1,
            "type":       "normal"
        }]
    }
    res = requests.post(f"{FREEE_BASE}/invoices", headers=freee_headers(), json=payload)
    if res.status_code in (200, 201):
        inv_id = res.json()["invoice"]["id"]
        print(f"  OK {entry['name']} / {entry['partner']} / {entry['seikyu']:,}円 [{entry['rule']}] -> ID:{inv_id}")
        return True
    else:
        print(f"  NG {entry['name']} / {res.status_code}: {res.text[:200]}")
        return False

# ===== メイン =====
def run(target_month=None):
    today = date.today()
    if target_month is None:
        target_month = (today.replace(day=1) + relativedelta(months=1))
    issue_date = target_month.replace(day=1)
    due_date   = issue_date + relativedelta(months=1) - relativedelta(days=1)

    print(f"=== freee請求書自動生成 v2 ===")
    print(f"請求対象月: {target_month.year}年{target_month.month}月分")
    print(f"請求日: {issue_date}  支払期限: {due_date}")
    print()

    entries = load_active_entries()
    print(f"対象人員: {len(entries)}名")
    for e in entries:
        print(f"  {e['source']} | {e['name']} | 粗利{e['profit']:,}円 | 請求{e['seikyu']:,}円 | {e['rule']}")
    print()

    ok = ng = 0
    for e in entries:
        if create_invoice(e, issue_date, due_date): ok += 1
        else: ng += 1

    print()
    print(f"=== 完了: 作成{ok}件 / エラー{ng}件 ===")
    print(f"-> https://secure.freee.co.jp/invoices")
    # ===== 請求書作成完了後: 契約マスターのステータスを自動更新 =====
    if ok > 0:
        try:
            import sys as _sys2
            import os as _os2
            _sys2.path.insert(0, _os2.path.dirname(__file__))
            from auto_status_update import update_status_after_invoice
            invoiced_names = [e["name"] for e in entries]
            print(f"\n[auto_status] 請求書作成済み人員のステータスを稼働中に更新...")
            update_status_after_invoice(names=invoiced_names)
        except Exception as _e:
            print(f"[auto_status] ステータス更新スキップ（エラー: {_e}）")

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1:
        y, m = map(int, _sys.argv[1].split("-"))
        run(date(y, m, 1))
    else:
        run()
