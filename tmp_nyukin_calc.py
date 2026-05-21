import sys, openpyxl
sys.stdout.reconfigure(encoding='utf-8')

EXCEL_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

def safe_int(v):
    if isinstance(v, (int, float)): return int(v)
    return 0

def is_valid_name(v):
    if v is None: return False
    if isinstance(v, (int, float)): return False
    import datetime
    if isinstance(v, (datetime.datetime, datetime.date)): return False
    s = str(v).strip()
    return s and s not in ("NaN", "稼働中合計") and not s.replace("/","").replace("-","").isdigit()

# ===== TERRA 支払サイト別に集計 =====
print("=== TERRA 支払サイト別集計 ===")
ws = wb["TERRA"]
rows = list(ws.iter_rows(values_only=True))
header_row = None
for i, row in enumerate(rows):
    if row and "担当" in str(row[0]) and "区分" in str(row[1] or ""):
        header_row = i
        break

terra_45 = 0; terra_60 = 0; terra_other = []
if header_row is not None:
    for row in rows[header_row+1:]:
        if not any(row): continue
        tantou = str(row[0] or "").strip()
        kubun  = str(row[1] or "").strip()
        status = str(row[2] or "").strip()
        name   = row[3]
        case   = str(row[6] or "").strip()
        tanka  = safe_int(row[7])
        shiire = safe_int(row[12])
        site   = safe_int(row[8])  # 支払サイト

        if "稼働中" not in status: continue
        if not is_valid_name(name): continue
        name = str(name).strip()

        is_gl_ft = any(k in case for k in ["グレイスライン","フラップテック","GL","FT","GL経由","FT経由"])
        profit = tanka - shiire

        if kubun == "P":
            if is_gl_ft: continue
            seikyu = 15000
        elif kubun == "BP":
            if tantou == "TERRA折半": seikyu = int(profit * 0.50)
            elif tantou == "岡本折半": seikyu = int(profit * 0.80)
            else: seikyu = int(profit * 0.80)
        else:
            seikyu = 15000
        if seikyu <= 0: continue

        if site <= 45:
            terra_45 += seikyu
            print(f"  45日: {name} {seikyu:,}円 (site={site})")
        else:
            terra_60 += seikyu
            print(f"  60日: {name} {seikyu:,}円 (site={site})")

print(f"  → TERRA 45日合計: {terra_45:,}円")
print(f"  → TERRA 60日合計: {terra_60:,}円")

# ===== FT 支払サイト別集計 =====
print("\n=== FT 支払サイト別集計 ===")
ws = wb["フラップテック"]
rows = list(ws.iter_rows(values_only=True))
header_row = None
for i, row in enumerate(rows):
    if row and "担当" in str(row[0]) and "ステータス" in str(row[1] or ""):
        header_row = i
        break

ft_45 = 0
if header_row is not None:
    for row in rows[header_row+1:]:
        if not any(row): continue
        tantou  = str(row[0] or "").strip()
        status  = str(row[1] or "").strip()
        name    = row[2]
        tanka   = safe_int(row[6])
        shiire  = safe_int(row[7])
        site    = safe_int(row[12])  # 支払サイト
        if "稼働中" not in status: continue
        if not is_valid_name(name): continue
        if tanka == 0: continue
        profit = tanka - shiire
        if profit <= 0: continue
        if tantou == "小坂折半": seikyu = int(profit * 0.48)
        else: seikyu = int(profit * 0.68)
        ft_45 += seikyu
        print(f"  {name}: seikyu={seikyu:,}円 (site={site})")

ft_45_inc = int(ft_45 * 1.1)
print(f"  → FT 合計(税抜): {ft_45:,}円 / 税込: {ft_45_inc:,}円")

# ===== GL 支払サイト別集計 =====
print("\n=== GL 支払サイト別集計 ===")
ws = wb["グレイスライン"]
rows = list(ws.iter_rows(values_only=True))
header_row = None
for i, row in enumerate(rows):
    if row and "ステータス" in str(row[0]):
        header_row = i
        break

gl_30 = 0; gl_45 = 0
if header_row is not None:
    for row in rows[header_row+1:]:
        if not any(row): continue
        status = str(row[0] or "").strip()
        name   = row[1]
        tanka  = safe_int(row[5])
        shiire = safe_int(row[6])
        site   = safe_int(row[10])  # 支払サイト
        if "稼働中" not in status: continue
        if not is_valid_name(name): continue
        if tanka == 0: continue
        profit = tanka - shiire
        if profit <= 0: continue
        seikyu = int(profit * 0.60)
        if site <= 30:
            gl_30 += seikyu
            print(f"  30日: {name} seikyu={seikyu:,}円")
        else:
            gl_45 += seikyu
            print(f"  45日: {name} seikyu={seikyu:,}円")

gl_30_inc = int(gl_30 * 1.1)
gl_45_inc = int(gl_45 * 1.1)
print(f"  → GL 30日合計: {gl_30:,}円(税込{gl_30_inc:,}円)")
print(f"  → GL 45日合計: {gl_45:,}円(税込{gl_45_inc:,}円)")

# ===== 入金予測サマリー =====
print("\n===== 5月稼働分 入金予測 =====")
print(f"[6月30日] GL 30日サイト: {gl_30_inc:,}円")

t45_src = int(terra_45 * 10.21 / 100)
t45_inc = int(terra_45 * 1.1)
t45_net = t45_inc - t45_src
t60_src = int(terra_60 * 10.21 / 100)
t60_inc = int(terra_60 * 1.1)
t60_net = t60_inc - t60_src

print(f"[7月15日] TERRA 45日: 税抜{terra_45:,} 源泉{t45_src:,} 税込{t45_inc:,} 実入り{t45_net:,}")
print(f"          GL 45日: {gl_45_inc:,}円(税込)")
print(f"          FT 45日: {ft_45_inc:,}円(税込)")
print(f"[7月31日] TERRA 60日: 税抜{terra_60:,} 源泉{t60_src:,} 税込{t60_inc:,} 実入り{t60_net:,}")

# 岡本払出は橋本奈緒（岡本折半）のFT分の半額
print("\n[岡本払出] 別途計算要（橋本奈緒分等）")
print("\n===== 4月稼働分（作成済請求書INV-99〜103）入金予測 =====")
print("6月1日:  GL 30日 42,000税抜 → 税込46,200円")
print("6月15日: TERRA 326,810(税抜) / FT 392,000税抜→税込431,200 / GL 84,000→税込92,400")
print("6月30日: TERRA 120,000(税抜)")
