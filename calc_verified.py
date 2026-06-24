# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ============================================================
# 6/1チャット確定前提に基づく厳密計算
# ============================================================
# 確定事項（過去チャット6/1）:
# - 鶴川: 6月入場 → 6月稼働→8月15日入金から発生
# - 佐々木(TERRA岡本折半): 4月開始 → 6月入金から発生
# - 橋本奈緒(FT岡本折半): 4月開始 → 6月入金から発生
# - 吉田祥平: 6月入場 → 8月入金から発生
# - 遠藤健太: 7月入場 → 9月入金から発生
# - 鶴見: 6月開始・翌月末 → 7月入金から発生
#
# TERRAの入金予測シート（Drive版確定値）:
# 6月: TERRA税抜475,000 / GL税抜108,000 / FT税抜371,600+20,400=392,000
# 7月: TERRA税抜475,000 / GL税抜108,000 / FT税抜419,200+20,400=439,600
# 8月: TERRA税抜485,000 / GL税抜108,000 / FT税抜375,200+20,400=395,600
# ※8月のFT395,600は原昌志退場後・鶴川なし・吉田FTなし状態（Drive版のまま）
#
# 岡本払出 月別:
# 6月:   TERRA3名27,000 + 佐々木20,000 + 橋本23,800 = 70,800（税抜）
# 7月:   70,800 + 鶴見50,000 = 120,800（税抜）
# 8月以降: 120,800 + 鶴川47,600 = 168,400（税抜）
#
# 木原さん分:
# 6月: 116,000円（原昌志含む）
# 8月以降: 96,000円（原退場後）


def calc(name, terra_zeinuki, gl_zeinuki, ft_zeinuki, okamoto_zeinuki, kihara, plus_items=None):
    """
    plus_items: [(名前, 税抜額, 種別)] 種別='TERRA'/'FT'/'直'
    """
    # TERRA
    terra_zeikomi = int(terra_zeinuki * 1.1)
    terra_gensen = int(terra_zeikomi * 0.1021)
    terra_jissyu = terra_zeikomi - terra_gensen

    # GL
    gl_zeikomi = int(gl_zeinuki * 1.1)

    # FT
    ft_zeikomi = int(ft_zeinuki * 1.1)

    # 追加項目（吉田祥平TERRA・吉田FT・遠藤・鶴見など）
    add_terra_zeinuki = 0
    add_ft_zeikomi = 0
    add_choku_zeikomi = 0
    add_lines = []

    if plus_items:
        for pname, pamount, pkind in plus_items:
            if pkind == "TERRA":
                add_terra_zeinuki += pamount
                add_lines.append(f"    +{pname} TERRA税抜{pamount:,}円")
            elif pkind == "FT":
                add_ft_zeikomi += int(pamount * 1.1)
                add_lines.append(f"    +{pname} FT税抜{pamount:,}円→税込{int(pamount * 1.1):,}円")
            elif pkind == "直":
                add_choku_zeikomi += pamount  # 直契約は税込で渡す
                add_lines.append(f"    +{pname} 税込{pamount:,}円")

    # 追加TERRA分の源泉も計算
    if add_terra_zeinuki:
        add_terra_zeikomi = int(add_terra_zeinuki * 1.1)
        add_terra_gensen = int(add_terra_zeikomi * 0.1021)
        add_terra_jissyu = add_terra_zeikomi - add_terra_gensen
        total_terra_gensen = terra_gensen + add_terra_gensen
        total_terra_jissyu = terra_jissyu + add_terra_jissyu
    else:
        add_terra_gensen = 0
        total_terra_gensen = terra_gensen
        total_terra_jissyu = terra_jissyu

    total_ft_zeikomi = ft_zeikomi + add_ft_zeikomi

    # 岡本払出・木原
    okamoto_zeikomi = int(okamoto_zeinuki * 1.1)

    # 合計
    tedori = total_terra_jissyu + gl_zeikomi + total_ft_zeikomi + add_choku_zeikomi - okamoto_zeikomi - kihara
    gengaku = tedori + total_terra_gensen

    print(f"\n{'=' * 65}", flush=True)
    print(f"◆ {name}", flush=True)
    print(f"{'=' * 65}", flush=True)

    total_t_z = terra_zeinuki + add_terra_zeinuki
    total_t_zk = int(total_t_z * 1.1)
    total_t_gs = total_terra_gensen
    print(
        f"[TERRA]  税抜{total_t_z:,}円 →税込{total_t_zk:,}円 -源泉{total_t_gs:,}円 = {total_terra_jissyu:,}円",
        flush=True,
    )
    print(f"[GL]     税抜{gl_zeinuki:,}円 →税込{gl_zeikomi:,}円", flush=True)
    total_ft_z = ft_zeinuki + int(add_ft_zeikomi / 1.1) if add_ft_zeikomi else ft_zeinuki
    print(
        f"[FT]     税抜{ft_zeinuki:,}円+ 追加{int(add_ft_zeikomi / 1.1):,}円 →税込合計{total_ft_zeikomi:,}円",
        flush=True,
    )
    if add_choku_zeikomi:
        print(f"[直契約]  税込{add_choku_zeikomi:,}円", flush=True)
    for l in add_lines:
        print(l, flush=True)
    print(f"[岡本払出] 税抜{okamoto_zeinuki:,}円 →税込{okamoto_zeikomi:,}円", flush=True)
    print(f"[木原分]  {kihara:,}円", flush=True)
    print(f"{'─' * 50}", flush=True)
    print(
        f"  手取り = {total_terra_jissyu:,}+{gl_zeikomi:,}+{total_ft_zeikomi:,}+{add_choku_zeikomi:,}-{okamoto_zeikomi:,}-{kihara:,}",
        flush=True,
    )
    print(f"  ★手取り合計: {tedori:,}円", flush=True)
    print(f"  TERRA源泉:  +{total_terra_gensen:,}円（確定申告還付）", flush=True)
    print(f"  ★額面:      {gengaku:,}円", flush=True)
    return tedori, gengaku


# ============================================================
# 6月入金（4月稼働分）
# - 鶴川6月開始なのでなし / 吉田なし / 遠藤なし / 鶴見なし
# - 佐々木4月開始→含む / 橋本4月開始→含む
# FT: Drive版6月入金の374,002ではなく、4月稼働確定値を使う
# Drive版6月入金: TERRA475,000 / GL108,000 / FT371,600+20,400=392,000
# 岡本払出: TERRA3名27,000+佐々木20,000+橋本23,800=70,800
# 木原: 116,000
# ============================================================
t6, g6 = calc(
    "6月入金（4月稼働分）",
    terra_zeinuki=475000,
    gl_zeinuki=108000,
    ft_zeinuki=392000,  # Drive版: 371,600+20,400
    okamoto_zeinuki=70800,  # TERRA3名+佐々木+橋本
    kihara=116000,
)

# ============================================================
# 7月入金（5月稼働分＋鶴見6月稼働→7月末入金）
# - 鶴川なし（6月開始→8月入金）/ 吉田なし / 遠藤なし
# - 鶴見あり（6月稼働→7月末）
# Drive版7月: TERRA475,000 / GL108,000 / FT419,200+20,400=439,600
# 岡本払出: TERRA3名+佐々木+橋本=70,800 + 鶴見50,000=120,800
# 木原: 116,000（原昌志5月末まで含む）
# 鶴見: 松野手取=100,000-50,000=50,000税抜→税込55,000
# ============================================================
t7, g7 = calc(
    "7月入金（5月稼働分）",
    terra_zeinuki=475000,
    gl_zeinuki=108000,
    ft_zeinuki=439600,  # Drive版
    okamoto_zeinuki=120800,  # +鶴見50,000
    kihara=116000,
    plus_items=[("鶴見(6月稼働→7月末)", 55000, "直")],  # 税込55,000
)

# ============================================================
# 8月入金（6月稼働分）
# - 鶴川6月入場→含む（実入り0、岡本全額47,600）
# - 吉田祥平6月入場→TERRA40,000税抜 + FT24,000税抜
# - 遠藤なし
# - 鶴見7月稼働→8月末
# Drive版8月: TERRA485,000（原退場後） / GL108,000 / FT395,600（原退場後）
# ※鶴川・吉田はDrive版未反映 → 追加
# 岡本払出: 70,800+鶴川47,600+鶴見50,000=168,400
# 木原: 96,000（原退場後）
# ============================================================
t8, g8 = calc(
    "8月入金（6月稼働分）",
    terra_zeinuki=485000,  # Drive版（原退場後）
    gl_zeinuki=108000,
    ft_zeinuki=395600,  # Drive版（原退場後・鶴川なし・吉田なし）
    okamoto_zeinuki=168400,  # +鶴川47,600+鶴見50,000
    kihara=96000,  # 原退場後
    plus_items=[
        ("吉田祥平TERRA", 40000, "TERRA"),  # 粗利5万×80%
        ("吉田祥平FT", 24000, "FT"),  # 粗利5万×48%
        ("鶴見(7月稼働→8月末)", 55000, "直"),
    ],
)

# ============================================================
# 9月入金（7月稼働分）
# - 8月と同構成 + 遠藤健太7月入場
# - 遠藤: FT岡本折半 粗利5万×68%÷2=17,000税抜 → 松野実入り17,000
#         岡本払出=17,000も追加
# 岡本払出: 168,400+遠藤17,000=185,400
# ============================================================
t9, g9 = calc(
    "9月入金（7月稼働分）",
    terra_zeinuki=485000,
    gl_zeinuki=108000,
    ft_zeinuki=395600,
    okamoto_zeinuki=185400,  # +遠藤17,000
    kihara=96000,
    plus_items=[
        ("吉田祥平TERRA", 40000, "TERRA"),
        ("吉田祥平FT", 24000, "FT"),
        ("遠藤健太FT", 17000, "FT"),  # 岡本折半だが松野実入り17,000
        ("鶴見(8月稼働→9月末)", 55000, "直"),
    ],
)

print(f"\n{'=' * 65}", flush=True)
print("【最終サマリー】", flush=True)
print(f"{'=' * 65}", flush=True)
print(f"{'月':<10}{'手取り(税込)':>15}{'TERRA源泉':>14}{'額面':>14}", flush=True)
print(f"{'─' * 55}", flush=True)

data = [
    ("6月入金", t6, g6),
    ("7月入金", t7, g7),
    ("8月入金", t8, g8),
    ("9月入金", t9, g9),
]
prev_t = None
for label, t, g in data:
    gs = g - t
    diff = f"({t - prev_t:+,})" if prev_t else ""
    print(f"{label:<10}{t:>14,}円{gs:>12,}円{g:>13,}円  {diff}", flush=True)
    prev_t = t

print("\n※手取り = TERRA税込実入り(源泉控除後) + GL税込 + FT税込 + 直契約 - 岡本払出税込 - 木原分", flush=True)
print("※額面  = 手取り + TERRA源泉（確定申告で全額還付）", flush=True)
