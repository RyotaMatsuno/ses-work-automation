# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 全稼働者の実入り・支払サイト・入金月を正確に計算
# 稼働月→入金月: サイト45日=翌々月15日, サイト40日=翌々月10日, サイト55日=翌々月末, サイト30日=翌月末

workers = [
    # (氏名, 種別, 実入り, サイト, 7月〜新規か, 備考)
    # TERRA プロパー 松野担当 15,000円
    ("仲山", "T松野", 15000, 45, False, ""),
    ("吉田創志", "T松野", 15000, 50, False, ""),
    ("蒲池", "T松野", 15000, 45, False, ""),
    ("大野", "T松野", 15000, 55, False, ""),
    ("白須", "T松野", 15000, 45, False, ""),
    ("沼田", "T松野", 15000, 55, False, ""),
    ("魚谷", "T松野", 15000, 55, False, ""),
    ("赤木", "T松野", 15000, 40, False, ""),
    ("坪井", "T松野", 15000, 50, False, ""),
    ("中村", "T松野", 15000, 50, False, ""),
    ("日比野", "T松野", 15000, 40, False, ""),
    ("永野", "T松野", 15000, 45, False, ""),
    ("安江", "T松野", 15000, 45, False, ""),
    ("相川", "T松野", 15000, 40, False, ""),
    ("富永", "T松野", 15000, 40, False, ""),
    # TERRA プロパー 岡本担当 6,000円
    ("天野", "T岡本", 6000, 50, False, "15,000-9,000"),
    ("岩瀬", "T岡本", 6000, 50, False, ""),
    ("加藤(T)", "T岡本", 6000, 45, False, ""),
    # TERRA BP折半
    ("森", "T折半", 30000, 40, False, "TERRA折半 粗利6万×50%"),
    ("芹澤", "T折半", 45000, 40, False, "TERRA折半 粗利9万×50%"),
    ("佐々木", "T岡本折半", 20000, 45, False, "岡本折半 粗利5万×80%÷2"),
    ("小山内", "T折半", 30000, 45, False, "TERRA折半 粗利6万×50%"),
    # 吉田祥平 7月〜 TERRA+FT両方請求
    ("吉田祥平_TERRA", "T松野", 40000, 45, True, "7月〜 TERRA粗利5万×80%=40,000"),
    ("吉田祥平_FT", "FT松野", 24000, 45, True, "7月〜 FP粗利5万×48%=24,000（小坂折半）"),
    # GL 松野担当
    ("石崎", "GL松野", 24000, 30, False, "GL粗利4万×60%=24,000（支払30日サイト=翌月末）"),
    ("山内清", "GL松野", 32000, 45, False, "GL粗利7万×60%=42,000-木原10,000=32,000"),
    ("荒井", "GL松野", 32000, 45, False, "GL粗利7万×60%=42,000-木原10,000=32,000"),
    # FT 各担当
    ("笠井", "FT松野", 58000, 45, False, "FT粗利10万×68%=68,000-木原10,000"),
    ("木村勇太", "FT松野", 37600, 45, False, "FT粗利7万×68%=47,600-木原10,000"),
    ("加藤FT", "FT小坂", 27400, 45, False, "FT小坂折半 粗利8万×48%=38,400-木原11,000"),
    ("川崎健太", "FT松野", 22200, 45, False, "FT粗利4万×68%=27,200-木原5,000"),
    ("田中みさ", "FT松野", 20400, 55, False, "FT粗利3万×68%=20,400 木原なし"),
    ("立野", "FT松野", 37600, 45, False, "FT粗利7万×68%=47,600-木原10,000"),
    ("佐々木駿", "FT松野", 7200, 45, False, "FT粗利4万×68%=27,200-木原20,000"),
    ("橋本", "FT岡本折半", 13800, 45, False, "FT粗利7万×68%=47,600÷2=23,800-木原10,000=13,800"),
    # 直契約
    ("鶴見有職研究所", "直契約", 50000, 30, False, "月10万-岡本5万 6月〜翌月末"),
    # 遠藤健太 7月〜
    ("遠藤健太", "FT岡本折半", 17000, 45, True, "FT粗利5万×68%=34,000÷2=17,000 7月〜"),
]


def get_nyukin_month(work_month, site):
    if site <= 30:
        return work_month + 1  # 翌月末
    elif site <= 45:
        return work_month + 2  # 翌々月15日
    elif site <= 55:
        return work_month + 2  # 翌々月末
    return work_month + 2


# 7・8・9月の集計
totals = {7: 0, 8: 0, 9: 0}
details = {7: [], 8: [], 9: []}

for name, kubun, jissyu, site, is_new_july, note in workers:
    for work_m, nyukin_m in [(5, 7), (6, 8), (7, 9)]:
        nm = get_nyukin_month(work_m, site)
        if nm != nyukin_m:
            continue
        # 7月〜新規は5・6月稼働分に含めない
        if is_new_july and work_m < 7:
            continue
        totals[nyukin_m] += jissyu
        details[nyukin_m].append((name, kubun, jissyu, note))

print("=" * 65, flush=True)
for m in [7, 8, 9]:
    print(f"\n■ {m}月入金  合計: {totals[m]:,}円", flush=True)
    for name, kubun, amt, note in details[m]:
        print(f"  {name}({kubun}) {amt:,}円  {note[:35]}", flush=True)

print("\n", flush=True)
print("【増減サマリー】", flush=True)
print(f"  7月: {totals[7]:,}円（基準）", flush=True)
print(f"  8月: {totals[8]:,}円（{totals[8] - totals[7]:+,}円）鶴見2ヶ月目 +50,000", flush=True)
print(f"  9月: {totals[9]:,}円（{totals[9] - totals[7]:+,}円）吉田+64,000・遠藤+17,000", flush=True)
