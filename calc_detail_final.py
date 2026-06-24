# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# 全稼働者の実入り・サイト・入金月を確定値から計算
# ============================================================


def nyukin_month(work_m, site):
    """稼働月とサイトから入金月を計算"""
    if site <= 30:
        return work_m + 1
    else:  # 40-55日は全て翌々月
        return work_m + 2


# ============================================================
# 稼働者マスター（契約マスターから読み取った確定値）
# format: (氏名, 種別, サイト, 開始月, 税抜単価, 税抜仕入, 備考)
# 実入り計算は種別ごとにロジックが異なる
# ============================================================

# --- TERRA ---
# プロパー: TERRA請求15,000円（税抜）→松野実入り
# TERRA折半BP: 粗利×50% → 松野実入り
# 岡本P: TERRA請求15,000 - 岡本払出9,000 = 6,000 → 松野実入り
# 岡本折半BP: 粗利×80% ÷ 2 → 松野実入り（TERRA折半扱い）

terra_workers = [
    # (氏名, 区分, サイト, 開始月, 案件単価, 仕入単価, 退場月)
    ("仲山雄輝", "P松野", 45, 1, 370000, None, None),
    ("吉田創志", "P松野", 50, 1, 430000, None, None),
    ("蒲池佑萌", "P松野", 45, 1, 400000, None, None),
    ("大野稔貴", "P松野", 55, 1, 320000, None, None),
    ("白須雄太", "P松野", 45, 1, 270000, None, None),
    ("沼田航陽", "P松野", 55, 1, 360000, None, None),
    ("魚谷", "P松野", 55, 1, 400000, None, None),
    ("赤木", "P松野", 40, 1, 400000, None, None),
    ("坪井", "P松野", 50, 1, 380000, None, None),
    ("中村", "P松野", 50, 1, 450000, None, None),
    ("日比野", "P松野", 40, 1, 400000, None, None),
    ("永野", "P松野", 45, 1, 680000, None, None),
    ("安江", "P松野", 45, 1, 480000, None, None),
    ("相川", "P松野", 40, 1, 400000, None, None),
    ("富永", "P松野", 40, 1, 360000, None, None),
    ("天野", "P岡本", 50, 1, 490000, None, None),  # 15,000-9,000=6,000
    ("岩瀬", "P岡本", 50, 1, 500000, None, None),
    ("加藤(T)", "P岡本", 45, 1, 380000, None, None),
    ("森", "BP折半", 40, 1, 380000, 320000, None),  # 粗利6万×50%=30,000
    ("芹澤", "BP折半", 40, 1, 590000, 500000, None),  # 粗利9万×50%=45,000
    ("佐々木(T)", "BP岡本折半", 45, 1, 610000, 560000, None),  # 粗利5万×80%÷2=20,000
    ("小山内", "BP折半", 45, 1, 600000, 540000, None),  # 粗利6万×50%=30,000
    ("吉田祥平", "P松野", 45, 7, 700000, 650000, None),  # 7月入場 TERRA粗利5万×80%=40,000
]


def calc_terra_jissyu(kubun, tanka, shiire):
    """TERRA実入り計算（税抜）"""
    if kubun == "P松野":
        return 15000
    elif kubun == "P岡本":
        return 6000  # 15,000 - 9,000
    elif kubun == "BP折半":
        gross = tanka - shiire
        return int(gross * 0.5)
    elif kubun == "BP岡本折半":
        gross = tanka - shiire
        return int(gross * 0.8 / 2)
    elif kubun == "P吉田":  # 特殊: TERRA粗利5万×80%
        return 40000
    return 0


# --- GL ---
# GL請求=粗利×60%、実入り=GL請求-木原さん分
# 石崎サイト30日、山内・荒井サイト45日
gl_workers = [
    # (氏名, サイト, 案件単価, 仕入単価, 木原分, 開始月)
    ("石崎春光", 30, 680000, 640000, 0, 1),  # 粗利4万×60%=24,000-木原0=24,000
    ("山内清", 45, 440000, 370000, 10000, 1),  # 粗利7万×60%=42,000-木原10,000=32,000
    ("荒井大輝", 45, 620000, 550000, 10000, 1),  # 粗利7万×60%=42,000-木原10,000=32,000
]


def calc_gl_jissyu(tanka, shiire, kihara):
    gross = tanka - shiire
    gl_req = int(gross * 0.6)
    return gl_req - kihara


# --- FT ---
# FT請求=粗利×68%(通常) or 粗利×48%(小坂折半)
# 岡本折半: FT請求÷2が岡本払出、残り-木原分が実入り
# 鶴川: FT請求47,600を満額岡本払出→実入り=0
# 通常: FT請求-木原分が実入り
ft_workers = [
    # (氏名, 区分, サイト, 案件単価, 仕入単価, 木原分, 開始月, 退場月)
    ("笠井健太", "通常", 45, 720000, 620000, 10000, 1, None),  # 粗利10万×68%-木原10,000=58,000
    ("木村勇太", "通常", 45, 670000, 600000, 10000, 1, None),  # 粗利7万×68%-木原10,000=37,600
    ("加藤(FT)", "小坂折半", 45, 630000, 550000, 11000, 1, None),  # 粗利8万×48%-木原11,000=27,400
    ("川崎健太", "通常", 45, 740000, 700000, 5000, 1, None),  # 粗利4万×68%-木原5,000=22,200
    ("田中みさ", "通常", 55, 430000, 400000, 0, 1, None),  # 粗利3万×68%=20,400
    ("立野和紀", "通常", 45, 520000, 450000, 10000, 1, None),  # 粗利7万×68%-木原10,000=37,600
    ("佐々木駿", "通常", 45, 650000, 610000, 20000, 1, None),  # 粗利4万×68%-木原20,000=7,200
    ("橋本奈緒", "岡本折半", 45, 570000, 500000, 10000, 1, None),  # 粗利7万×68%÷2-木原10,000=13,800
    ("鶴川慶三", "岡本全額", 45, 720000, 650000, 0, 5, None),  # FT請求47,600→全額岡本払出→実入り0
    ("吉田祥平", "小坂折半", 45, 750000, 700000, 0, 6, None),  # 粗利5万×48%=24,000（木原なし）
    ("遠藤健太", "岡本折半", 45, 600000, 550000, 0, 7, None),  # 粗利5万×68%÷2=17,000（木原なし）
]


def calc_ft_jissyu(kubun, tanka, shiire, kihara):
    gross = tanka - shiire
    if kubun == "通常":
        ft_req = int(gross * 0.68)
        return ft_req - kihara
    elif kubun == "小坂折半":
        ft_req = int(gross * 0.48)
        return ft_req - kihara
    elif kubun == "岡本折半":
        ft_req = int(gross * 0.68)
        return int(ft_req / 2) - kihara
    elif kubun == "岡本全額":
        return 0  # 全額岡本払出
    return 0


# ============================================================
# 月別集計（6・7・8・9月入金）
# ============================================================

results = {6: {}, 7: {}, 8: {}, 9: {}}

for m_nyukin in [6, 7, 8, 9]:
    lines = []

    # TERRA
    terra_zeinuki_total = 0
    for name, kubun, site, start_m, tanka, shiire, taijo_m in terra_workers:
        # 入金月に対応する稼働月を逆算
        work_m = m_nyukin - (1 if site <= 30 else 2)
        if work_m < start_m:
            continue
        if taijo_m and work_m >= taijo_m:
            continue
        # 吉田祥平はTERRA側で特別処理
        if name == "吉田祥平":
            jissyu_zeinuki = 40000
        else:
            jissyu_zeinuki = calc_terra_jissyu(kubun, tanka, shiire)
        terra_zeinuki_total += jissyu_zeinuki
        lines.append(("TERRA", name, jissyu_zeinuki, site, kubun, ""))

    # TERRAまとめて税込・源泉計算
    terra_zeikomi = int(terra_zeinuki_total * 1.1)
    terra_gensen = int(terra_zeikomi * 0.1021)
    terra_jissyu_zeikomi = terra_zeikomi - terra_gensen
    results[m_nyukin]["terra_zeinuki"] = terra_zeinuki_total
    results[m_nyukin]["terra_gensen"] = terra_gensen
    results[m_nyukin]["terra_jissyu"] = terra_jissyu_zeikomi
    results[m_nyukin]["terra_lines"] = lines

    # GL
    gl_total = 0
    gl_lines = []
    for name, site, tanka, shiire, kihara, start_m in gl_workers:
        work_m = m_nyukin - (1 if site <= 30 else 2)
        if work_m < start_m:
            continue
        jissyu_zeinuki = calc_gl_jissyu(tanka, shiire, kihara)
        jissyu_zeikomi = int(jissyu_zeinuki * 1.1)
        gl_total += jissyu_zeikomi
        gl_lines.append(("GL", name, jissyu_zeinuki, jissyu_zeikomi, site, kihara))
    results[m_nyukin]["gl_total"] = gl_total
    results[m_nyukin]["gl_lines"] = gl_lines

    # FT
    ft_total = 0
    ft_okamoto_total_zeinuki = 0
    ft_lines = []
    for name, kubun, site, tanka, shiire, kihara, start_m, taijo_m in ft_workers:
        work_m = m_nyukin - 2  # FTは全員サイト45or55→翌々月
        if name == "田中みさ":
            work_m = m_nyukin - 2  # サイト55も翌々月
        if work_m < start_m:
            continue
        if taijo_m and work_m >= taijo_m:
            continue
        gross = tanka - shiire
        if kubun == "通常":
            ft_req = int(gross * 0.68)
            ok_pay = 0
            jissyu = ft_req - kihara
        elif kubun == "小坂折半":
            ft_req = int(gross * 0.48)
            ok_pay = 0
            jissyu = ft_req - kihara
        elif kubun == "岡本折半":
            ft_req = int(gross * 0.68)
            ok_pay = int(ft_req / 2)
            jissyu = ok_pay - kihara  # 松野実入り = ft_req - ok_pay - kihara
            jissyu = ft_req - ok_pay - kihara
        elif kubun == "岡本全額":
            ft_req = int(gross * 0.68)
            ok_pay = ft_req
            jissyu = 0
        else:
            ft_req = 0
            ok_pay = 0
            jissyu = 0
        ft_total += int(jissyu * 1.1)
        ft_okamoto_total_zeinuki += ok_pay
        ft_lines.append(("FT", name, kubun, gross, ft_req, ok_pay, jissyu, kihara, site))
    results[m_nyukin]["ft_total"] = ft_total
    results[m_nyukin]["ft_okamoto"] = ft_okamoto_total_zeinuki
    results[m_nyukin]["ft_lines"] = ft_lines

    # 直契約（鶴見）: 6月稼働→7月末、以降毎月
    tsurumi_jissyu = 0
    if m_nyukin >= 7:  # 6月稼働→7月入金が初回
        tsurumi_jissyu = 50000  # 税抜5万（請求10万-岡本5万）
    tsurumi_zeikomi = int(tsurumi_jissyu * 1.1) if tsurumi_jissyu else 0
    results[m_nyukin]["tsurumi"] = tsurumi_zeikomi

# ============================================================
# 出力
# ============================================================

print("=" * 70, flush=True)
print("【月別 詳細内訳 + 合計】", flush=True)
print("=" * 70, flush=True)

for m in [6, 7, 8, 9]:
    r = results[m]
    print(f"\n{'=' * 70}", flush=True)
    print(f"◆ {m}月入金", flush=True)
    print(f"{'=' * 70}", flush=True)

    print(
        f"\n[TERRA] 税抜合計:{r['terra_zeinuki']:,}円 → 税込:{int(r['terra_zeinuki'] * 1.1):,}円 - 源泉:{r['terra_gensen']:,}円 = 実入り:{r['terra_jissyu']:,}円",
        flush=True,
    )
    for _, name, jissyu, site, kubun, _ in r["terra_lines"]:
        print(f"  {name}({kubun}) サイト{site}日 税抜{jissyu:,}円 → 税込{int(jissyu * 1.1):,}円", flush=True)

    print(f"\n[GL] 税込合計:{r['gl_total']:,}円", flush=True)
    for _, name, zeinuki, zeikomi, site, kihara in r["gl_lines"]:
        print(f"  {name} サイト{site}日 税抜{zeinuki:,}円 → 税込{zeikomi:,}円（木原{kihara:,}円控除後）", flush=True)

    print(f"\n[FT] 税込実入り合計:{r['ft_total']:,}円", flush=True)
    for _, name, kubun, gross, ft_req, ok_pay, jissyu, kihara, site in r["ft_lines"]:
        jissyu_zeikomi = int(jissyu * 1.1)
        print(
            f"  {name}({kubun}) サイト{site}日 粗利{gross:,} FT請求{ft_req:,} 岡本払{ok_pay:,} 木原{kihara:,} → 実入り税抜{jissyu:,}円/税込{jissyu_zeikomi:,}円",
            flush=True,
        )

    if r["tsurumi"]:
        print(f"\n[直契約] 鶴見有職研究所 税込:{r['tsurumi']:,}円（請求10万-岡本払5万=手取5万×1.1）", flush=True)

    # 合計
    total_tedori = r["terra_jissyu"] + r["gl_total"] + r["ft_total"] + r["tsurumi"]
    total_gengaku = total_tedori + r["terra_gensen"]
    print(f"\n{'─' * 50}", flush=True)
    print(f"  TERRA実入り(税込・源泉後): {r['terra_jissyu']:,}円", flush=True)
    print(f"  GL実入り(税込):            {r['gl_total']:,}円", flush=True)
    print(f"  FT実入り(税込):            {r['ft_total']:,}円", flush=True)
    if r["tsurumi"]:
        print(f"  鶴見(税込):                {r['tsurumi']:,}円", flush=True)
    print(f"{'─' * 50}", flush=True)
    print(f"  ★手取り合計:  {total_tedori:,}円", flush=True)
    print(f"  TERRA源泉:   +{r['terra_gensen']:,}円（確定申告で還付）", flush=True)
    print(f"  ★額面合計:    {total_gengaku:,}円", flush=True)
