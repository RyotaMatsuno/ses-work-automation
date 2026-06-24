import os
import sys
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())
import sheets_reader as SR

ss = SR._open()


def gv(row, i):
    return row[i].strip() if i < len(row) and row[i] else ""


def to_int(s):
    try:
        return int(str(s).replace(",", "").replace("¥", "").strip())
    except Exception:
        return 0


INCLUDE_END = "5月末終了"


def included(status):
    return ("稼働中" in status) or (INCLUDE_END in status)


# バケット化: TR/GL → 30/45/46、FT → 45固定
def bucket(partner, site):
    if "フラップテック" in partner:
        return "45"
    s = to_int(site)
    if s <= 30:
        return "30"
    if s <= 45:
        return "45"
    return "46"


people = []
warn = []

# TERRA
for row in ss.worksheet("TERRA").get_all_values()[4:]:
    name = gv(row, 3)
    if not name or name in ("氏名", "稼働中合計"):
        continue
    status = gv(row, 2)
    kubun = gv(row, 1)
    site = gv(row, 8)
    case = gv(row, 6)
    tanka = to_int(gv(row, 7))
    shiire = to_int(gv(row, 13))
    tantou = gv(row, 0)
    if not included(status):
        continue
    if kubun == "P" and any(k in case for k in ["グレイスライン", "フラップテック", "GL", "FT"]):
        warn.append(f"TERRA {name}: GL/FT経由→TERRA計上せず")
        continue
    if not site:
        warn.append(f"TERRA {name}: サイト/単価空白→除外")
        continue
    if kubun == "P":
        pm = (11 / 18) if name == "齋藤よしまさ" else 1.0
        people.append({"partner": "株式会社TERRA", "name": name, "site": site, "prop": True, "pm": pm})
    else:
        profit = tanka - shiire
        if tantou == "TERRA折半":
            amt = int(profit * 0.50)
        elif tantou == "岡本折半":
            amt = int(profit * 0.80)
        else:
            amt = int(profit * 0.80)
        people.append({"partner": "株式会社TERRA", "name": name, "site": site, "prop": False, "amount": amt})

# FT
for row in ss.worksheet("フラップテック").get_all_values()[3:]:
    name = gv(row, 2)
    if not name or name in ("氏名",):
        continue
    status = gv(row, 1)
    tantou = gv(row, 0)
    site = gv(row, 12)
    tanka = to_int(gv(row, 6))
    shiire = to_int(gv(row, 7))
    if not included(status):
        continue
    if not site:
        warn.append(f"FT {name}: サイト空白→除外")
        continue
    profit = tanka - shiire
    amt = int(profit * 0.48) if tantou == "小坂折半" else int(profit * 0.68)
    people.append({"partner": "株式会社フラップテック", "name": name, "site": site, "prop": False, "amount": amt})

# GL (サイトはSheet空白→過去確定値)
GL_SITE = {"石崎春光": "30", "山内清": "45", "荒井大輝": "45"}
for row in ss.worksheet("グレイスライン").get_all_values()[3:]:
    name = gv(row, 1)
    if not name or name in ("氏名",):
        continue
    status = gv(row, 0)
    tanka = to_int(gv(row, 5))
    shiire = to_int(gv(row, 6))
    if not included(status):
        continue
    site = GL_SITE.get(name, "")
    if not site:
        warn.append(f"GL {name}: サイト不明→除外")
        continue
    people.append(
        {
            "partner": "グレイスライン株式会社",
            "name": name,
            "site": site,
            "prop": False,
            "amount": int((tanka - shiire) * 0.60),
        }
    )


def pay_date(bk):
    d = date(2026, 5, 31) + timedelta(days=int(bk))
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


from collections import defaultdict

groups = defaultdict(list)
for p in people:
    groups[(p["partner"], bucket(p["partner"], p["site"]))].append(p)

GENSHEN = "株式会社TERRA"
total_all = 0
n = 0
for partner, bk in sorted(groups, key=lambda x: (x[0], int(x[1]))):
    ppl = groups[(partner, bk)]
    n += 1
    props = [p for p in ppl if p.get("prop")]
    inds = [p for p in ppl if not p.get("prop")]
    lines = []
    if props:
        pm = sum(p["pm"] for p in props)
        lines.append((f"プロパー稼働分(数量{round(pm, 2)})", round(15000 * pm), ",".join(p["name"] for p in props)))
    for p in inds:
        lines.append((f"{p['name']}様稼働分", p["amount"], ""))
    sub = sum(a for _, a, _ in lines)
    tax = int(sub * 0.10)
    gen = int(sub * 0.1021) if partner == GENSHEN else 0
    tot = sub + tax - gen
    total_all += tot
    print(f"■ {partner} / {bk}日請求 / 支払期限{pay_date(bk)} / 源泉{'あり' if gen else 'なし'} / 合計{tot:,}円")
    for d, a, note in lines:
        print(f"    - {d}: {a:,}円 {('[' + note + ']') if note else ''}")
    print(f"      税抜{sub:,}+税{tax:,}-源泉{gen:,}")
print(f"\n=== {n}枚 / 合計(源泉控除後) {total_all:,}円 ===")
print("=== 除外 ===")
for w in warn:
    print("  ・", w)
