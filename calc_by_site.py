# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 支払サイト別 入金月の正確な計算
# 稼働月 → 入金月
# サイト30日 = 翌月末
# サイト40日 = 翌々月10日
# サイト45日 = 翌々月15日
# サイト50日 = 翌々月20日
# サイト55日 = 翌々月末
# 直契約（鶴見）= 翌月末（月末締め翌月最終営業日）

# 全稼働者リスト
# (氏名, 種別, 税抜実入り, サイト, 開始月, 備考)
workers = [
    # TERRA プロパー 松野担当 15,000円/人 × 15人 = 225,000
    ("TERRA松野プロパー15名", "TERRA", 225000, 45, 5, ""),  # 5月〜継続
    # TERRA 岡本担当 6,000円/人 × 3人 = 18,000
    ("TERRA岡本プロパー3名", "TERRA", 18000, 50, 5, "天野50日・岩瀬50日・加藤T45日 → 最遅の50日で計算"),
    # TERRA BP折半
    ("森", "TERRA", 30000, 40, 5, "TERRA折半 粗利6万×50%"),
    ("芹澤", "TERRA", 45000, 40, 5, "TERRA折半 粗利9万×50%"),
    ("佐々木BP", "TERRA", 20000, 45, 5, "岡本折半 粗利5万×80%÷2"),
    ("小山内", "TERRA", 30000, 45, 5, "TERRA折半 粗利6万×50%"),
    # 吉田祥平 TERRA分 7月〜 サイト45日
    ("吉田祥平_TERRA", "TERRA", 40000, 45, 7, "TERRA粗利5万×80%=4万 7月〜"),
    # GL
    ("石崎", "GL", 24000, 30, 5, "GL粗利4万×60%=24,000 サイト30日"),
    ("山内清", "GL", 32000, 45, 5, "GL粗利7万×60%=42,000-木原10,000=32,000"),
    ("荒井", "GL", 32000, 45, 5, "GL粗利7万×60%=42,000-木原10,000=32,000"),
    # FT
    ("笠井", "FT", 58000, 45, 5, "FT粗利10万×68%=68,000-木原10,000"),
    ("木村勇太", "FT", 37600, 45, 5, "FT粗利7万×68%=47,600-木原10,000"),
    ("加藤FT小坂", "FT", 27400, 45, 5, "FT小坂折半 粗利8万×48%=38,400-木原11,000"),
    ("川崎健太", "FT", 22200, 45, 5, "FT粗利4万×68%=27,200-木原5,000"),
    ("田中みさ", "FT", 20400, 55, 5, "FT粗利3万×68%=20,400 サイト55日"),
    ("立野", "FT", 37600, 45, 5, "FT粗利7万×68%=47,600-木原10,000"),
    ("佐々木駿", "FT", 7200, 45, 5, "FT粗利4万×68%=27,200-木原20,000"),
    ("橋本", "FT", 13800, 45, 5, "FT岡本折半 粗利7万×68%÷2=23,800-木原10,000"),
    ("吉田祥平_FT", "FT", 24000, 45, 7, "FP粗利5万×48%=24,000（小坂折半）7月〜"),
    ("遠藤健太", "FT", 17000, 45, 7, "FT岡本折半 粗利5万×68%÷2=17,000 7月〜"),
    # 直契約
    ("鶴見有職研究所", "直契約", 50000, 30, 6, "月10万-岡本5万=松野5万 6月〜翌月末"),
]


def get_nyukin_month(work_month, site):
    if site <= 30:
        return work_month + 1
    elif site <= 45:
        return work_month + 2
    elif site <= 55:
        return work_month + 2
    return work_month + 2


# 6・7・8・9月入金の計算
print("=" * 70, flush=True)
print("【支払サイト別 入金月計算】", flush=True)
print("=" * 70, flush=True)

# 各稼働者の稼働月→入金月対応を表示
for name, kubun, jissyu, site, start_m, note in workers:
    for work_m in [4, 5, 6, 7]:
        if work_m < start_m:
            continue
        nyukin_m = get_nyukin_month(work_m, site)
        if nyukin_m in [6, 7, 8, 9]:
            print(f"  {name}({kubun}) {work_m}月稼働→{nyukin_m}月入金 {jissyu:,}円 [サイト{site}]", flush=True)

print("\n", flush=True)

# 月別集計
totals = {6: 0, 7: 0, 8: 0, 9: 0}
details = {6: [], 7: [], 8: [], 9: []}

for name, kubun, jissyu, site, start_m, note in workers:
    for work_m in [4, 5, 6, 7]:
        if work_m < start_m:
            continue
        nyukin_m = get_nyukin_month(work_m, site)
        if nyukin_m in [6, 7, 8, 9]:
            totals[nyukin_m] += jissyu
            details[nyukin_m].append((name, kubun, jissyu, work_m, site))

print("=" * 70, flush=True)
print("【月別 税抜実入り合計（岡本払出・木原分控除後）】", flush=True)
print("=" * 70, flush=True)

for m in [6, 7, 8, 9]:
    print(f"\n■ {m}月入金  税抜合計: {totals[m]:,}円  →  税込: {int(totals[m] * 1.1):,}円", flush=True)
    for name, kubun, amt, work_m, site in details[m]:
        print(f"  {name} {work_m}月稼働 {amt:,}円 [サイト{site}日]", flush=True)

print("\n", flush=True)
print("【TERRA源泉額の確認（確定申告で戻る分）】", flush=True)
# TERRAの税抜請求額×10.21%
terra_amounts = {
    6: 475000,  # Drive版6月入金予測より
    7: 475000,
    8: 485000,  # 吉田加算後
    9: 485000,
}
for m in [6, 7, 8, 9]:
    gensen = int(terra_amounts[m] * 0.1021)
    print(f"  {m}月: TERRA請求(税抜){terra_amounts[m]:,}円 × 10.21% = 源泉{gensen:,}円", flush=True)
