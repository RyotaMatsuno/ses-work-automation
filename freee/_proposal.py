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


INCLUDE_END = "5月末終了"  # 5月稼働分の対象に含める


def included(status):
    return ("稼働中" in status) or (INCLUDE_END in status)


people = []  # dict: partner, name, kubun, site, amount, prop(bool), pm(person-month for プロパー)
warn = []

# ---- TERRA ----
data = ss.worksheet("TERRA").get_all_values()
for row in data[4:]:
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
    is_glft = any(k in case for k in ["グレイスライン", "フラップテック", "GL", "FT"])
    if kubun == "P" and is_glft:
        warn.append(f"TERRA {name}: P だが案件「{case}」(GL/FT経由)→TERRA請求なし(他社経由で計上)")
        continue
    if not site:
        warn.append(f"TERRA {name}: 支払サイト空白(単価={tanka or '空'})→要確認のため除外")
        continue
    if kubun == "P":
        pm = (11 / 18) if name == "齋藤よしまさ" else 1.0
        people.append(
            {
                "partner": "株式会社TERRA",
                "name": name,
                "site": site,
                "prop": True,
                "pm": pm,
                "amount": round(15000 * pm),
            }
        )
    else:  # BP
        profit = tanka - shiire
        if tantou == "TERRA折半":
            amt, rule = int(profit * 0.50), "TERRA折半×50%"
        elif tantou == "岡本折半":
            amt, rule = int(profit * 0.80), "岡本折半×80%"
        else:
            amt, rule = int(profit * 0.80), "BP×80%"
        people.append(
            {"partner": "株式会社TERRA", "name": name, "site": site, "prop": False, "amount": amt, "rule": rule}
        )

# ---- フラップテック ----
data = ss.worksheet("フラップテック").get_all_values()
for row in data[3:]:
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
        warn.append(f"FT {name}: 支払サイト空白→除外")
        continue
    profit = tanka - shiire
    if tantou == "小坂折半":
        amt = int(profit * 0.48)
    else:
        amt = int(profit * 0.68)
    people.append({"partner": "株式会社フラップテック", "name": name, "site": site, "prop": False, "amount": amt})

# ---- グレイスライン (サイトはSheet空白→過去確定値で補完) ----
GL_SITE = {"石崎春光": "30", "山内清": "45", "荒井大輝": "45"}
data = ss.worksheet("グレイスライン").get_all_values()
for row in data[3:]:
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
    profit = tanka - shiire
    amt = int(profit * 0.60)
    people.append({"partner": "グレイスライン株式会社", "name": name, "site": site, "prop": False, "amount": amt})


# ---- 支払期限 = 2026-05-31 + サイト日数（土日は翌営業日・簡易） ----
def pay_date(site):
    d = date(2026, 5, 31) + timedelta(days=int(site))
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


# ---- 取引先×サイトでグループ化して請求書を組む ----
from collections import defaultdict

groups = defaultdict(list)
for p in people:
    groups[(p["partner"], p["site"])].append(p)

genshen_partner = "株式会社TERRA"  # 源泉あり
total_all = 0
n_inv = 0
for partner, site in sorted(groups, key=lambda x: (x[0], int(x[1]))):
    ppl = groups[(partner, site)]
    n_inv += 1
    props = [p for p in ppl if p.get("prop")]
    inds = [p for p in ppl if not p.get("prop")]
    lines = []
    if props:
        pm = sum(p["pm"] for p in props)
        amt = round(15000 * pm)
        names = ",".join(p["name"] for p in props)
        lines.append((f"プロパー稼働分(数量{round(pm, 2)})", amt, names))
    for p in inds:
        lines.append((f"{p['name']}様稼働分", p["amount"], p.get("rule", "")))
    subtotal = sum(a for _, a, _ in lines)
    tax = int(subtotal * 0.10)
    gen = int(subtotal * 0.1021) if partner == genshen_partner else 0
    total = subtotal + tax - gen
    total_all += total
    print(
        f"■ {partner} / サイト{site}日 / 件名「5月分請求書」 / 請求日2026-06-01 / 支払期限{pay_date(site)} / 源泉{'あり' if gen else 'なし'}"
    )
    for desc, amt, note in lines:
        print(f"    - {desc}: {amt:,}円   {('<' + note + '>') if note else ''}")
    print(f"    税抜{subtotal:,} + 消費税{tax:,} - 源泉{gen:,} = 合計 {total:,}円")
print(f"\n=== 請求書 {n_inv}枚 / 合計(源泉控除後) {total_all:,}円 ===")
print("\n=== 要確認・除外 ===")
for w in warn:
    print("  ・", w)
