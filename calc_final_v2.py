# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# Drive版確定値との照合で判明した正しい源泉計算式:
# 源泉 = TERRA税抜請求額 × 10.21%（税込ではなく税抜に対してかかる）
# Drive版6月: TERRA税抜475,000 × 10.21% = 48,497 ≒ 48,498
# TERRA実入り = 税抜475,000×1.1 - 源泉48,498 = 522,500-48,498 = 474,002 ✅
# ============================================================


def calc_month(name, terra_zeinuki, gl_zeinuki, ft_zeinuki_base, okamoto_zeinuki, kihara, plus_items=None):
    """
    plus_items: [(名前, 税抜額, 種別)]
      種別: 'TERRA' = TERRA側追加（源泉対象）
            'FT'    = FT追加（源泉なし）
            '直'    = 直契約（税込で渡す、源泉なし）
    """
    # TERRA基本
    terra_zeikomi = int(terra_zeinuki * 1.1)
    terra_gensen = int(terra_zeinuki * 0.1021)  # ← 税抜ベース
    terra_jissyu = terra_zeikomi - terra_gensen

    gl_zeikomi = int(gl_zeinuki * 1.1)
    ft_zeikomi = int(ft_zeinuki_base * 1.1)

    add_terra_gensen = 0
    add_terra_jissyu = 0
    add_ft_zeikomi = 0
    add_choku = 0

    plus_detail = []
    if plus_items:
        for pname, pamount, pkind in plus_items:
            if pkind == "TERRA":
                gs = int(pamount * 0.1021)
                jissyu = int(pamount * 1.1) - gs
                add_terra_gensen += gs
                add_terra_jissyu += jissyu
                plus_detail.append(f"    +{pname}: 税抜{pamount:,} 源泉{gs:,} 実入り{jissyu:,}円")
            elif pkind == "FT":
                zk = int(pamount * 1.1)
                add_ft_zeikomi += zk
                plus_detail.append(f"    +{pname}: 税抜{pamount:,}→税込{zk:,}円")
            elif pkind == "直":
                add_choku += pamount  # 税込で受け取る
                plus_detail.append(f"    +{pname}: 税込{pamount:,}円")

    total_terra_gensen = terra_gensen + add_terra_gensen
    total_terra_jissyu = terra_jissyu + add_terra_jissyu
    total_ft_zeikomi = ft_zeikomi + add_ft_zeikomi
    total_terra_zeinuki = terra_zeinuki + sum(p[1] for p in (plus_items or []) if p[2] == "TERRA")

    okamoto_zeikomi = int(okamoto_zeinuki * 1.1)

    tedori = total_terra_jissyu + gl_zeikomi + total_ft_zeikomi + add_choku - okamoto_zeikomi - kihara
    gengaku = tedori + total_terra_gensen

    print(f"\n{'=' * 65}", flush=True)
    print(f"◆ {name}", flush=True)
    print(f"{'=' * 65}", flush=True)
    print(
        f"[TERRA]  税抜{total_terra_zeinuki:,} 税込{int(total_terra_zeinuki * 1.1):,} -源泉{total_terra_gensen:,} = 実入り{total_terra_jissyu:,}円",
        flush=True,
    )
    print(f"[GL]     税抜{gl_zeinuki:,} →税込{gl_zeikomi:,}円", flush=True)
    print(f"[FT]     税抜base{ft_zeinuki_base:,}+追加 →税込{total_ft_zeikomi:,}円", flush=True)
    for d in plus_detail:
        print(d, flush=True)
    print(f"[岡本払出] 税抜{okamoto_zeinuki:,} →税込{okamoto_zeikomi:,}円", flush=True)
    print(f"[木原分]  {kihara:,}円", flush=True)
    print(f"{'─' * 50}", flush=True)
    print(
        f"  手取り:{total_terra_jissyu:,}+{gl_zeikomi:,}+{total_ft_zeikomi:,}+{add_choku:,}-{okamoto_zeikomi:,}-{kihara:,} = {tedori:,}円",
        flush=True,
    )
    print(f"  ★手取り: {tedori:,}円", flush=True)
    print(f"  TERRA源泉: +{total_terra_gensen:,}円", flush=True)
    print(f"  ★額面:    {gengaku:,}円", flush=True)
    return tedori, gengaku, total_terra_gensen


# 6月（4月稼働）鶴川なし/吉田なし/遠藤なし/鶴見なし
t6, g6, gs6 = calc_month(
    "6月入金（4月稼働）",
    terra_zeinuki=475000,
    gl_zeinuki=108000,
    ft_zeinuki_base=392000,  # Drive版: 371,600+20,400
    okamoto_zeinuki=70800,  # TERRA3名+佐々木+橋本
    kihara=116000,
)

# 7月（5月稼働＋鶴見6月稼働→7月末）鶴川なし/吉田なし/遠藤なし
t7, g7, gs7 = calc_month(
    "7月入金（5月稼働＋鶴見初回）",
    terra_zeinuki=475000,
    gl_zeinuki=108000,
    ft_zeinuki_base=439600,  # Drive版
    okamoto_zeinuki=120800,  # +鶴見50,000
    kihara=116000,
    plus_items=[("鶴見6月稼働→7月末", 55000, "直")],
)

# 8月（6月稼働）鶴川あり/吉田あり/遠藤なし/鶴見あり
t8, g8, gs8 = calc_month(
    "8月入金（6月稼働）",
    terra_zeinuki=485000,  # Drive版（原退場後）
    gl_zeinuki=108000,
    ft_zeinuki_base=395600,  # Drive版（原退場後）
    okamoto_zeinuki=168400,  # +鶴川47,600+鶴見50,000
    kihara=96000,  # 原退場後
    plus_items=[
        ("吉田TERRA", 40000, "TERRA"),
        ("吉田FT", 24000, "FT"),
        ("鶴見7月稼働→8月末", 55000, "直"),
    ],
)

# 9月（7月稼働）遠藤追加
t9, g9, gs9 = calc_month(
    "9月入金（7月稼働）",
    terra_zeinuki=485000,
    gl_zeinuki=108000,
    ft_zeinuki_base=395600,
    okamoto_zeinuki=185400,  # +遠藤17,000
    kihara=96000,
    plus_items=[
        ("吉田TERRA", 40000, "TERRA"),
        ("吉田FT", 24000, "FT"),
        ("遠藤健太", 17000, "FT"),
        ("鶴見8月稼働→9月末", 55000, "直"),
    ],
)

print(f"\n{'=' * 65}", flush=True)
print("【最終サマリー】", flush=True)
print(f"{'=' * 65}", flush=True)
print(f"{'月':<12}{'手取り':>13}{'TERRA源泉':>12}{'額面':>12}", flush=True)
print(f"{'─' * 52}", flush=True)
rows = [("6月", t6, g6, gs6), ("7月", t7, g7, gs7), ("8月", t8, g8, gs8), ("9月", t9, g9, gs9)]
prev = None
for lbl, t, g, gs in rows:
    diff = f"({t - prev:+,})" if prev is not None else ""
    print(f"{lbl}入金{'':<5}{t:>12,}円{gs:>10,}円{g:>11,}円  {diff}", flush=True)
    prev = t

# 検証: Drive版6月確定値との照合
print("\n【Drive版確定値との照合】", flush=True)
print(f"  6月 Drive版: 787,202円  今回計算: {t6:,}円  差: {t6 - 787202:+,}円", flush=True)
print("  7月 Drive版: 825,282円（鶴見・追加前）", flush=True)
print(f"  過去チャット確定 7月: 937,482円  今回計算: {t7:,}円  差: {t7 - 937482:+,}円", flush=True)
