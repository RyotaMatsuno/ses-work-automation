
"""
2026年度 入金予測 一括生成スクリプト
"""
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
from dateutil.relativedelta import relativedelta
import calendar

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

# ============================
# 人員マスター（現在の稼働情報）
# ============================
# type: TERRA_P / TERRA_BP / GL / FT
# site: 支払いサイト日数
# amount: 月次請求額（税抜=TERRA, 税込=GL/FT）
# okamoto: 岡本払出額/月
# start: 稼働開始年月 (year, month)
# end: 終了年月 (year, month) or None=継続

STAFF = [
    # --- TERRA プロパー（請求あり） ---
    {"name":"仲山雄輝",   "type":"TERRA_P", "site":45, "amount":15000, "okamoto":0, "start":(2023,12)},
    {"name":"吉田創志",   "type":"TERRA_P", "site":50, "amount":15000, "okamoto":0, "start":(2024,3)},
    {"name":"蒲池佑萌",   "type":"TERRA_P", "site":45, "amount":15000, "okamoto":0, "start":(2024,3)},
    {"name":"大野稔貴",   "type":"TERRA_P", "site":55, "amount":15000, "okamoto":0, "start":(2024,4)},
    {"name":"白須雄太",   "type":"TERRA_P", "site":45, "amount":15000, "okamoto":0, "start":(2024,5)},
    {"name":"沼田航陽",   "type":"TERRA_P", "site":55, "amount":15000, "okamoto":0, "start":(2024,6)},
    {"name":"魚谷",       "type":"TERRA_P", "site":55, "amount":15000, "okamoto":0, "start":(2025,4), "end":(2026,4)},
    {"name":"赤木",       "type":"TERRA_P", "site":40, "amount":15000, "okamoto":0, "start":(2025,7)},
    {"name":"坪井",       "type":"TERRA_P", "site":50, "amount":15000, "okamoto":0, "start":(2025,7)},
    {"name":"中村",       "type":"TERRA_P", "site":50, "amount":15000, "okamoto":0, "start":(2025,8)},
    {"name":"日比野",     "type":"TERRA_P", "site":40, "amount":15000, "okamoto":0, "start":(2025,9)},
    {"name":"永野",       "type":"TERRA_P", "site":45, "amount":15000, "okamoto":0, "start":(2025,10)},
    {"name":"安江",       "type":"TERRA_P", "site":45, "amount":15000, "okamoto":0, "start":(2025,10)},
    {"name":"相川",       "type":"TERRA_P", "site":40, "amount":15000, "okamoto":0, "start":(2025,10)},
    {"name":"芹澤_P扱",  "type":"SKIP",    "site":0,  "amount":0,     "okamoto":0, "start":(2025,12)},  # BPで別途
    {"name":"富永",       "type":"TERRA_P", "site":40, "amount":15000, "okamoto":0, "start":(2026,1)},
    {"name":"天野",       "type":"TERRA_P", "site":50, "amount":15000, "okamoto":9000, "start":(2026,1)},   # 岡本担当
    {"name":"岩瀬",       "type":"TERRA_P", "site":50, "amount":15000, "okamoto":9000, "start":(2026,3)},   # 岡本担当
    {"name":"加藤(T)",    "type":"TERRA_P", "site":45, "amount":15000, "okamoto":9000, "start":(2026,3)},   # 岡本担当
    {"name":"橋詰(新)",   "type":"TERRA_P", "site":45, "amount":15000, "okamoto":0, "start":(2026,4)},
    {"name":"佐々木(入)", "type":"TERRA_P", "site":45, "amount":15000, "okamoto":0, "start":(2026,4)},
    {"name":"片山",       "type":"TERRA_P", "site":30, "amount":15000, "okamoto":0, "start":(2025,4), "end":(2026,5)},
    {"name":"齋藤よしまさ","type":"TERRA_P","site":45, "amount":15000, "okamoto":0, "start":(2026,5)},
    # --- TERRA BP ---
    {"name":"大本(BP)",   "type":"TERRA_BP","site":35, "amount":15000, "okamoto":0,  "start":(2025,9),  "end":(2026,5)},
    {"name":"森(BP)",     "type":"TERRA_BP","site":40, "amount":30000, "okamoto":0,  "start":(2025,9)},
    {"name":"芹澤(BP)",   "type":"TERRA_BP","site":40, "amount":45000, "okamoto":0,  "start":(2025,12)},
    {"name":"佐々木(TERRA)","type":"TERRA_BP","site":45,"amount":40000,"okamoto":20000,"start":(2026,4)}, # 岡本折半
    {"name":"小山内(BP)", "type":"TERRA_BP","site":45, "amount":30000, "okamoto":0,  "start":(2026,4)},
    {"name":"吉田祥平(TERRA)","type":"TERRA_BP","site":45,"amount":40000,"okamoto":0,"start":(2026,6)}, # 小坂折半
    # --- GL (税込) ---
    {"name":"石崎(GL)",   "type":"GL", "site":30, "amount":24000, "okamoto":0, "start":(2024,9)},
    {"name":"山内清(GL)", "type":"GL", "site":45, "amount":42000, "okamoto":0, "start":(2024,10)},
    {"name":"荒井大輝(GL)","type":"GL","site":45, "amount":42000, "okamoto":0, "start":(2025,6)},
    # --- FT (税込) ---
    {"name":"笠井健太(FT)","type":"FT","site":45, "amount":68000, "okamoto":0, "start":(2026,2)},
    {"name":"原昌志(FT)", "type":"FT","site":45, "amount":68000, "okamoto":0, "start":(2026,3), "end":(2026,5)},
    {"name":"木村勇太(FT)","type":"FT","site":45, "amount":47600, "okamoto":0, "start":(2026,3)},
    {"name":"加藤(FT)",   "type":"FT","site":45, "amount":38400, "okamoto":0, "start":(2026,3)},  # 小坂折半
    {"name":"川崎健太(FT)","type":"FT","site":45, "amount":27200, "okamoto":0, "start":(2026,4)},
    {"name":"田中みさ(FT)","type":"FT","site":55, "amount":20400, "okamoto":0, "start":(2026,4)},
    {"name":"立野和紀(FT)","type":"FT","site":45, "amount":47600, "okamoto":0, "start":(2026,4)},
    {"name":"佐々木駿(FT)","type":"FT","site":45, "amount":27200, "okamoto":0, "start":(2026,4)},
    {"name":"橋本奈緒(FT)","type":"FT","site":45, "amount":47600, "okamoto":23800,"start":(2026,4)},  # 岡本折半
    {"name":"吉田祥平(FT)","type":"FT","site":45, "amount":24000, "okamoto":0, "start":(2026,6)},  # 小坂折半
    {"name":"鶴川慶三(FT)","type":"FT","site":45, "amount":47600, "okamoto":9520, "start":(2026,5)},  # 岡本新営業
]

def is_active(staff, year, month):
    sy, sm = staff["start"]
    if (year, month) < (sy, sm): return False
    if "end" in staff:
        ey, em = staff["end"]
        if (year, month) > (ey, em): return False
    return True

def calc_payment_date(work_year, work_month, site):
    """稼働月→請求月末→サイト日数後の入金日を計算"""
    # 翌月末 = 請求発行日
    invoice_month = date(work_year, work_month, 1) + relativedelta(months=1)
    invoice_end = date(invoice_month.year, invoice_month.month,
                       calendar.monthrange(invoice_month.year, invoice_month.month)[1])
    # 入金日 = 請求日 + サイト日数
    pay_date = invoice_end + relativedelta(days=site)
    return pay_date

# ============================
# 2026年度（4月〜翌3月）の入金予測計算
# ============================
from collections import defaultdict

# {(pay_year, pay_month, day_type): {terra_p:, terra_bp:, gl:, ft:, okamoto:}}
# day_type: 15 or 31(=末)
results = defaultdict(lambda: {"terra_p":0,"terra_bp":0,"gl":0,"ft":0,"okamoto":0,"source_months":[]})

for work_year in [2026, 2027]:
    for work_month in range(1, 13):
        # 2026年4月〜2027年3月のみ
        if (work_year, work_month) < (2026, 4): continue
        if (work_year, work_month) > (2027, 3): continue

        for s in STAFF:
            if s["type"] == "SKIP": continue
            if not is_active(s, work_year, work_month): continue

            pay_date = calc_payment_date(work_year, work_month, s["site"])
            py, pm = pay_date.year, pay_date.month

            # 15日か末日かで分類（シンプル化: ≤15日→15日, >15日→末日）
            if pay_date.day <= 17:
                day_key = 15
            else:
                day_key = 31

            key = (py, pm, day_key)
            results[key]["source_months"].append(f"{work_year}/{work_month}")

            t = s["type"]
            if t == "TERRA_P":
                results[key]["terra_p"] += s["amount"]
            elif t == "TERRA_BP":
                results[key]["terra_bp"] += s["amount"]
            elif t == "GL":
                results[key]["gl"] += s["amount"]
            elif t == "FT":
                results[key]["ft"] += s["amount"]
            results[key]["okamoto"] += s["okamoto"]

# ============================
# シートデータ作成
# ============================
GENTEN_RATE = 0.1021

rows = []
rows.append(["入金予測（2026年度 4月〜2027年3月）", "", "", "", "", "", "", "", "", "", ""])
rows.append(["※TERRA：請求額(税抜)×10.21%を源泉控除　GL/FT：税込がそのまま実入り", "", "", "", "", "", "", "", "", "", ""])
rows.append(["入金予定日","稼働月","TERRA\n請求(税抜)","源泉徴収\n(税抜×10.21%)",
             "TERRA\n税込入金","TERRA\n実入り\n(税込-源泉)","GL\n税込","FT\n税込","岡本払出","木原さん分","総実入り"])

sorted_keys = sorted(results.keys())

current_pay_month = None
month_subtotals = {"terra_p":0,"terra_bp":0,"gl":0,"ft":0,"okamoto":0,"total":0}

for key in sorted_keys:
    py, pm, day_key = key
    pay_year_month = (py, pm)

    # 月ヘッダー
    if pay_year_month != current_pay_month:
        # 前月の小計行
        if current_pay_month:
            cy, cm = current_pay_month
            terra_sub = month_subtotals["terra_p"] + month_subtotals["terra_bp"]
            genten_sub = round(terra_sub * GENTEN_RATE)
            terra_tax_sub = round(terra_sub * 1.1)
            terra_real_sub = terra_tax_sub - genten_sub
            gl_sub = month_subtotals["gl"]
            ft_sub = month_subtotals["ft"]
            ok_sub = month_subtotals["okamoto"]
            # 木原さん分（GL/FTから一部）- 今回は省略（入力が必要）
            total_sub = terra_real_sub + gl_sub + ft_sub - ok_sub
            rows.append([f"{cy}年{cm}月 小計","",terra_sub,genten_sub,terra_tax_sub,terra_real_sub,gl_sub,ft_sub,ok_sub,"",total_sub])
            rows.append(["","","","","","","","","","",""])
            month_subtotals = {"terra_p":0,"terra_bp":0,"gl":0,"ft":0,"okamoto":0,"total":0}

        current_pay_month = pay_year_month
        rows.append([f"◆ {py}年{pm}月 入金分", "", "", "", "", "", "", "", "", "", ""])

    d = results[key]
    terra = d["terra_p"] + d["terra_bp"]
    gl = d["gl"]
    ft = d["ft"]
    ok = d["okamoto"]

    if terra > 0:
        genten = round(terra * GENTEN_RATE)
        terra_tax = round(terra * 1.1)
        terra_real = terra_tax - genten
    else:
        genten = terra_tax = terra_real = 0

    total = terra_real + gl + ft - ok
    day_str = f"{py}/{pm:02d}/{day_key:02d}"

    # 稼働月リスト（重複除去してソート）
    source = ", ".join(sorted(set(d["source_months"])))

    rows.append([day_str, source,
                 terra if terra else "-",
                 genten if genten else "-",
                 terra_tax if terra_tax else "-",
                 terra_real if terra_real else "-",
                 gl if gl else "-",
                 ft if ft else "-",
                 ok if ok else "-",
                 "-",
                 total])

    month_subtotals["terra_p"] += d["terra_p"]
    month_subtotals["terra_bp"] += d["terra_bp"]
    month_subtotals["gl"] += d["gl"]
    month_subtotals["ft"] += d["ft"]
    month_subtotals["okamoto"] += d["okamoto"]

# 最後の月小計
if current_pay_month:
    cy, cm = current_pay_month
    terra_sub = month_subtotals["terra_p"] + month_subtotals["terra_bp"]
    genten_sub = round(terra_sub * GENTEN_RATE)
    terra_tax_sub = round(terra_sub * 1.1)
    terra_real_sub = terra_tax_sub - genten_sub
    gl_sub = month_subtotals["gl"]
    ft_sub = month_subtotals["ft"]
    ok_sub = month_subtotals["okamoto"]
    total_sub = terra_real_sub + gl_sub + ft_sub - ok_sub
    rows.append([f"{cy}年{cm}月 小計","",terra_sub,genten_sub,terra_tax_sub,terra_real_sub,gl_sub,ft_sub,ok_sub,"",total_sub])

# 年度合計
rows.append(["","","","","","","","","","",""])
rows.append(["2026年度 総合計（4月〜2027年3月稼働分）", "", "", "", "", "", "", "", "", "", ""])

import json
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\nyukin_yosoku.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print(f"計算完了: {len(rows)}行")
# プレビュー
for r in rows[:20]:
    print(r)
