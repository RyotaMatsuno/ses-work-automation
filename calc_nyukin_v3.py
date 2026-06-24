"""
入金予測 v3: 木原さん分マイナス追加
"""

import calendar
from collections import defaultdict
from datetime import date

import gspread
from dateutil.relativedelta import relativedelta
from google.oauth2.service_account import Credentials

CREDS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\google_credentials.json"
SS_ID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)
gc = gspread.authorize(creds)
ss = gc.open_by_key(SS_ID)

# kihara: 木原さん分（月次）
STAFF = [
    # TERRA P
    {"name": "仲山雄輝", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2023, 12)},
    {"name": "吉田創志", "t": "TP", "site": 50, "amt": 15000, "ok": 0, "kh": 0, "s": (2024, 3)},
    {"name": "蒲池佑萌", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2024, 3)},
    {"name": "大野稔貴", "t": "TP", "site": 55, "amt": 15000, "ok": 0, "kh": 0, "s": (2024, 4)},
    {"name": "白須雄太", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2024, 5)},
    {"name": "沼田航陽", "t": "TP", "site": 55, "amt": 15000, "ok": 0, "kh": 0, "s": (2024, 6)},
    {"name": "魚谷", "t": "TP", "site": 55, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 4), "e": (2026, 4)},
    {"name": "赤木", "t": "TP", "site": 40, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 7)},
    {"name": "坪井", "t": "TP", "site": 50, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 7)},
    {"name": "中村", "t": "TP", "site": 50, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 8)},
    {"name": "日比野", "t": "TP", "site": 40, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 9)},
    {"name": "永野", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 10)},
    {"name": "安江", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 10)},
    {"name": "相川", "t": "TP", "site": 40, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 10)},
    {"name": "富永", "t": "TP", "site": 40, "amt": 15000, "ok": 0, "kh": 0, "s": (2026, 1)},
    {"name": "天野", "t": "TP", "site": 50, "amt": 15000, "ok": 9000, "kh": 0, "s": (2026, 1)},
    {"name": "岩瀬", "t": "TP", "site": 50, "amt": 15000, "ok": 9000, "kh": 0, "s": (2026, 3)},
    {"name": "加藤(T)", "t": "TP", "site": 45, "amt": 15000, "ok": 9000, "kh": 0, "s": (2026, 3)},
    {"name": "橋詰(新)", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2026, 4)},
    {"name": "佐々木(入)", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2026, 4)},
    {"name": "片山", "t": "TP", "site": 30, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 4), "e": (2026, 5)},
    {"name": "齋藤よしまさ", "t": "TP", "site": 45, "amt": 15000, "ok": 0, "kh": 0, "s": (2026, 5)},
    # TERRA BP
    {"name": "大本", "t": "TB", "site": 35, "amt": 15000, "ok": 0, "kh": 0, "s": (2025, 9), "e": (2026, 5)},
    {"name": "森", "t": "TB", "site": 40, "amt": 30000, "ok": 0, "kh": 0, "s": (2025, 9)},
    {"name": "芹澤", "t": "TB", "site": 40, "amt": 45000, "ok": 0, "kh": 0, "s": (2025, 12)},
    {"name": "佐々木(TERRA)", "t": "TB", "site": 45, "amt": 40000, "ok": 20000, "kh": 0, "s": (2026, 4)},
    {"name": "小山内", "t": "TB", "site": 45, "amt": 30000, "ok": 0, "kh": 0, "s": (2026, 4)},
    {"name": "吉田祥平(TR)", "t": "TB", "site": 45, "amt": 40000, "ok": 0, "kh": 0, "s": (2026, 6)},
    # GL（木原さん分あり）
    {"name": "石崎", "t": "GL", "site": 30, "amt": 24000, "ok": 0, "kh": 0, "s": (2024, 9)},
    {"name": "山内清(GL)", "t": "GL", "site": 45, "amt": 42000, "ok": 0, "kh": 10000, "s": (2024, 10)},
    {"name": "荒井", "t": "GL", "site": 45, "amt": 42000, "ok": 0, "kh": 10000, "s": (2025, 6)},
    # FT（木原さん分あり）
    {"name": "笠井健太", "t": "FT", "site": 45, "amt": 68000, "ok": 0, "kh": 10000, "s": (2026, 2)},
    {"name": "原昌志", "t": "FT", "site": 45, "amt": 68000, "ok": 0, "kh": 20000, "s": (2026, 3), "e": (2026, 5)},
    {"name": "木村勇太(FT)", "t": "FT", "site": 45, "amt": 47600, "ok": 0, "kh": 10000, "s": (2026, 3)},
    {"name": "加藤(FT)", "t": "FT", "site": 45, "amt": 38400, "ok": 0, "kh": 11000, "s": (2026, 3)},
    {"name": "川崎健太", "t": "FT", "site": 45, "amt": 27200, "ok": 0, "kh": 5000, "s": (2026, 4)},
    {"name": "田中みさ(FT)", "t": "FT", "site": 55, "amt": 20400, "ok": 0, "kh": 0, "s": (2026, 4)},
    {"name": "立野和紀", "t": "FT", "site": 45, "amt": 47600, "ok": 0, "kh": 10000, "s": (2026, 4)},
    {"name": "佐々木駿", "t": "FT", "site": 45, "amt": 27200, "ok": 0, "kh": 20000, "s": (2026, 4)},
    {"name": "橋本奈緒", "t": "FT", "site": 45, "amt": 47600, "ok": 23800, "kh": 10000, "s": (2026, 4)},
    {"name": "吉田祥平(FT)", "t": "FT", "site": 45, "amt": 24000, "ok": 0, "kh": 0, "s": (2026, 6)},
    {"name": "鶴川慶三", "t": "FT", "site": 45, "amt": 47600, "ok": 9520, "kh": 0, "s": (2026, 5)},
]


def active(s, y, m):
    if (y, m) < s["s"]:
        return False
    if "e" in s and (y, m) > s["e"]:
        return False
    return True


def pay_key(wy, wm, site):
    pm = date(wy, wm, 1) + relativedelta(months=2)
    return (pm.year, pm.month, 15 if site <= 45 else 99)


GENTEN = 0.1021

buckets = defaultdict(lambda: {"TP": 0, "TB": 0, "GL": 0, "FT": 0, "OK": 0, "KH": 0, "names": []})
for wy in [2026, 2027]:
    for wm in range(1, 13):
        if (wy, wm) < (2026, 4) or (wy, wm) > (2027, 3):
            continue
        for s in STAFF:
            if not active(s, wy, wm):
                continue
            k = pay_key(wy, wm, s["site"])
            buckets[k][s["t"]] += s["amt"]
            buckets[k]["OK"] += s["ok"]
            buckets[k]["KH"] += s["kh"]
            buckets[k]["names"].append(f"{wy}/{wm}")

rows = []
rows += [
    ["入金予測（2026年度 4月稼働分〜2027年3月稼働分）", "", "", "", "", "", "", "", "", "", ""],
    [
        "※TERRA：請求額(税抜)×10.21%を源泉控除　GL/FT：税込がそのまま実入り　※木原さん分・岡本払出はマイナス計上",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ],
    [
        "入金予定日",
        "稼働月",
        "TERRA\n請求(税抜)",
        "源泉徴収\n(×10.21%)",
        "TERRA\n税込",
        "TERRA\n実入り",
        "GL\n税込",
        "FT\n税込",
        "岡本払出\n(△)",
        "木原さん分\n(△後渡し)",
        "総実入り",
    ],
]


def last_day(y, m):
    return calendar.monthrange(y, m)[1]


cur_ym = None
ym = {"terra": 0, "gl": 0, "ft": 0, "ok": 0, "kh": 0}
annual = {"terra": 0, "gl": 0, "ft": 0, "ok": 0, "kh": 0, "real": 0}

for k in sorted(buckets.keys()):
    py, pm, dt = k
    if (py, pm) != cur_ym:
        if cur_ym:
            cy, cm = cur_ym
            t = ym["terra"]
            g = round(t * GENTEN)
            tx = round(t * 1.1)
            ri = tx - g
            tot = ri + ym["gl"] + ym["ft"] - ym["ok"] - ym["kh"]
            rows.append([f"{cy}年{cm}月 小計", "", t, g, tx, ri, ym["gl"], ym["ft"], -ym["ok"], -ym["kh"], tot])
            rows.append(["", "", "", "", "", "", "", "", "", "", ""])
            annual["terra"] += t
            annual["gl"] += ym["gl"]
            annual["ft"] += ym["ft"]
            annual["ok"] += ym["ok"]
            annual["kh"] += ym["kh"]
            annual["real"] += tot
            ym = {"terra": 0, "gl": 0, "ft": 0, "ok": 0, "kh": 0}
        cur_ym = (py, pm)
        rows.append([f"◆ {py}年{pm}月 入金分", "", "", "", "", "", "", "", "", "", ""])

    b = buckets[k]
    terra = b["TP"] + b["TB"]
    gl = b["GL"]
    ft = b["FT"]
    ok = b["OK"]
    kh = b["KH"]
    g = round(terra * GENTEN)
    tx = round(terra * 1.1)
    ri = tx - g
    tot = ri + gl + ft - ok - kh
    dd = 15 if dt == 15 else last_day(py, pm)
    src = ", ".join(sorted(set(b["names"])))
    rows.append(
        [
            f"{py}/{pm:02d}/{dd:02d}",
            src,
            terra if terra else "-",
            g if g else "-",
            tx if tx else "-",
            ri if ri else "-",
            gl if gl else "-",
            ft if ft else "-",
            -ok if ok else "-",
            -kh if kh else "-",
            tot,
        ]
    )
    ym["terra"] += terra
    ym["gl"] += gl
    ym["ft"] += ft
    ym["ok"] += ok
    ym["kh"] += kh

# 最終月
if cur_ym:
    cy, cm = cur_ym
    t = ym["terra"]
    g = round(t * GENTEN)
    tx = round(t * 1.1)
    ri = tx - g
    tot = ri + ym["gl"] + ym["ft"] - ym["ok"] - ym["kh"]
    rows.append([f"{cy}年{cm}月 小計", "", t, g, tx, ri, ym["gl"], ym["ft"], -ym["ok"], -ym["kh"], tot])
    annual["terra"] += t
    annual["gl"] += ym["gl"]
    annual["ft"] += ym["ft"]
    annual["ok"] += ym["ok"]
    annual["kh"] += ym["kh"]
    annual["real"] += tot

rows.append(["", "", "", "", "", "", "", "", "", "", ""])
g = round(annual["terra"] * GENTEN)
tx = round(annual["terra"] * 1.1)
ri = tx - g
rows.append(
    [
        "2026年度 年間総合計",
        "",
        annual["terra"],
        g,
        tx,
        ri,
        annual["gl"],
        annual["ft"],
        -annual["ok"],
        -annual["kh"],
        annual["real"],
    ]
)

ws = ss.worksheet("入金予測")
ws.clear()
ws.update(rows, "A1")

print(f"完了: {len(rows)}行")
print("\n=== 2026年度 年間見込み ===")
print(f"  TERRA請求(税抜): {annual['terra']:,}")
print(f"  GL(税込):        {annual['gl']:,}")
print(f"  FT(税込):        {annual['ft']:,}")
print(f"  岡本払出(△):     {annual['ok']:,}")
print(f"  木原さん分(△):   {annual['kh']:,}")
print(f"  年間総実入り:    {annual['real']:,}")
