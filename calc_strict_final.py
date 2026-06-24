# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ===== 厳密計算（過去チャット6/1の最終確定式に基づく）=====
# 全数字税込×1.1ベース、TERRAのみ源泉控除

# 岡本払出（全項目）税抜
okamoto_payouts_tax_excluded = {
    "TERRA岡本3名": 27000,  # 9,000×3名
    "佐々木(岡本折半)": 20000,  # 粗利5万×80%÷2
    "橋本(岡本折半)": 23800,  # 粗利7万×68%÷2=47,600÷2
    "鶴川(満額)": 47600,  # 粗利7万×68%=47,600全額
    "鶴見": 50000,  # 月10万固定÷2
}
total_okamoto_tax_excluded = sum(okamoto_payouts_tax_excluded.values())
total_okamoto_tax_included = int(total_okamoto_tax_excluded * 1.1)

print("【岡本払出 合計】", flush=True)
for k, v in okamoto_payouts_tax_excluded.items():
    print(f"  {k}: 税抜{v:,}円 / 税込{int(v * 1.1):,}円", flush=True)
print(f"  合計: 税抜{total_okamoto_tax_excluded:,}円 / 税込{total_okamoto_tax_included:,}円", flush=True)

print("\n" + "=" * 70, flush=True)
print("【月別 厳密計算】", flush=True)
print("=" * 70, flush=True)

# ============ 6月入金（4月稼働分）============
# 4月稼働なので鶴見・吉田祥平・遠藤・鶴川なし
print("\n■ 6月入金（4月稼働分）", flush=True)
print("  4月稼働分なので鶴見/吉田/遠藤/鶴川なし。Drive版確定値そのまま", flush=True)
june_tedori = 787202  # Drive版確定値
june_gensen = 48498  # Drive版より
june_gengaku = june_tedori + june_gensen
print(f"  手取り: {june_tedori:,}円", flush=True)
print(f"  TERRA源泉: +{june_gensen:,}円", flush=True)
print(f"  ★額面: {june_gengaku:,}円", flush=True)

# ============ 7月入金（5月稼働分）============
# 5月稼働: 鶴川5月入場で含まれる、鶴見6月開始なので含まれない、吉田祥平6月入場なので含まれない
print("\n■ 7月入金（5月稼働分）", flush=True)

# TERRA税抜（5月稼働分・原昌志含む）
terra_zeinuki_5 = 475000  # Drive版確定値
terra_zeikomi_5 = int(terra_zeinuki_5 * 1.1)
terra_gensen_5 = int(terra_zeikomi_5 * 0.1021)
terra_jissyu_5 = terra_zeikomi_5 - terra_gensen_5
print(
    f"  TERRA: 税抜{terra_zeinuki_5:,}→税込{terra_zeikomi_5:,}-源泉{terra_gensen_5:,}={terra_jissyu_5:,}円", flush=True
)

# GL税抜（5月稼働分）
gl_zeinuki_5 = 108000  # Drive版確定値
gl_zeikomi_5 = int(gl_zeinuki_5 * 1.1)
print(f"  GL: 税抜{gl_zeinuki_5:,}→税込{gl_zeikomi_5:,}円", flush=True)

# FT税抜（5月稼働分・鶴川含む、原昌志含む、吉田祥平なし、遠藤なし）
# Drive版5月稼働FT = 439,600（原昌志5月末まで稼働）
ft_zeinuki_5 = 439600
ft_zeikomi_5 = int(ft_zeinuki_5 * 1.1)
print(f"  FT: 税抜{ft_zeinuki_5:,}→税込{ft_zeikomi_5:,}円", flush=True)

# 鶴見（6月開始なので5月稼働分なし、ただし6月稼働→7月末入金あり）
# 7月入金には「5月稼働分FT/GL/TERRA」と「6月稼働分鶴見」が混在する
tsurumi_zeikomi_7 = 110000  # 鶴見6月稼働分は税込110,000円が7月末入金
print(f"  鶴見(6月稼働→7月末入金): 税込{tsurumi_zeikomi_7:,}円", flush=True)

# 岡本払出（5月稼働分: TERRA3名+佐々木+橋本+鶴川=141,400税抜）
# 鶴見は5月稼働分にはないが、6月稼働分の岡本払出を7月末に行う
# 鶴見の岡本払出は5万→税込55,000円も7月末に控除される
okamoto_5_excluded = 27000 + 20000 + 23800 + 47600  # 鶴見除く（5月稼働分）= 118,400
okamoto_5_included = int(okamoto_5_excluded * 1.1)
tsurumi_okamoto_7 = 55000  # 鶴見岡本払出（6月稼働分→7月末）
print(f"  岡本払出(5月稼働): 税抜{okamoto_5_excluded:,}→税込{okamoto_5_included:,}円", flush=True)
print(f"  岡本払出(鶴見6月分): 税込{tsurumi_okamoto_7:,}円", flush=True)

# 木原さん分（5月稼働分・原昌志含む）
kihara_7 = 116000
print(f"  木原さん分: 税込{kihara_7:,}円", flush=True)

# 7月入金合計
july_tedori = (
    terra_jissyu_5 + gl_zeikomi_5 + ft_zeikomi_5 + tsurumi_zeikomi_7 - okamoto_5_included - tsurumi_okamoto_7 - kihara_7
)
july_gengaku = july_tedori + terra_gensen_5
print(f"  ★手取り: {july_tedori:,}円", flush=True)
print(f"  TERRA源泉: +{terra_gensen_5:,}円", flush=True)
print(f"  ★額面: {july_gengaku:,}円", flush=True)

# ============ 8月入金（6月稼働分）============
print("\n■ 8月入金（6月稼働分）", flush=True)
# 6月稼働: 鶴川○、鶴見○、吉田祥平○（6月入場）、遠藤×、原昌志×（5月末退場）

# TERRA税抜（6月稼働: 原昌志退場、吉田祥平TERRA追加）
# Drive版6月稼働TERRA=485,000 + 吉田TERRA税抜40,000 = 525,000
terra_zeinuki_6 = 525000
terra_zeikomi_6 = int(terra_zeinuki_6 * 1.1)  # 577,500
terra_gensen_6 = int(terra_zeikomi_6 * 0.1021)  # 58,962
terra_jissyu_6 = terra_zeikomi_6 - terra_gensen_6
print(
    f"  TERRA: 税抜{terra_zeinuki_6:,}→税込{terra_zeikomi_6:,}-源泉{terra_gensen_6:,}={terra_jissyu_6:,}円", flush=True
)

# GL税抜（6月稼働分）
gl_zeinuki_6 = 108000
gl_zeikomi_6 = int(gl_zeinuki_6 * 1.1)
print(f"  GL: 税抜{gl_zeinuki_6:,}→税込{gl_zeikomi_6:,}円", flush=True)

# FT税抜（6月稼働: 原昌志退場、吉田祥平FT追加）
# Drive版6月稼働FT=395,600(原退場後) + 吉田FT税抜24,000 = 419,600
ft_zeinuki_6 = 419600
ft_zeikomi_6 = int(ft_zeinuki_6 * 1.1)
print(f"  FT: 税抜{ft_zeinuki_6:,}→税込{ft_zeikomi_6:,}円", flush=True)

# 鶴見（7月稼働分→8月末入金）
tsurumi_zeikomi_8 = 110000
print(f"  鶴見(7月稼働→8月末): 税込{tsurumi_zeikomi_8:,}円", flush=True)

# 岡本払出（6月稼働: TERRA3名+佐々木+橋本+鶴川=118,400 + 鶴見50,000）
okamoto_6_excluded = 118400  # 鶴見除く
okamoto_6_included = int(okamoto_6_excluded * 1.1)
tsurumi_okamoto_8 = 55000
print(f"  岡本払出(6月稼働): 税抜{okamoto_6_excluded:,}→税込{okamoto_6_included:,}円", flush=True)
print(f"  岡本払出(鶴見7月分): 税込{tsurumi_okamoto_8:,}円", flush=True)

# 木原さん分（原退場で減少）
kihara_8 = 96000
print(f"  木原さん分(原退場後): 税込{kihara_8:,}円", flush=True)

aug_tedori = (
    terra_jissyu_6 + gl_zeikomi_6 + ft_zeikomi_6 + tsurumi_zeikomi_8 - okamoto_6_included - tsurumi_okamoto_8 - kihara_8
)
aug_gengaku = aug_tedori + terra_gensen_6
print(f"  ★手取り: {aug_tedori:,}円", flush=True)
print(f"  TERRA源泉: +{terra_gensen_6:,}円", flush=True)
print(f"  ★額面: {aug_gengaku:,}円", flush=True)

# ============ 9月入金（7月稼働分）============
print("\n■ 9月入金（7月稼働分）", flush=True)
# 7月稼働: 6月稼働構成 + 遠藤健太

# TERRA・GL・FTは6月稼働と同構成（魚谷5月末未退場ならそのまま）
# 9月入金=8月入金 + 遠藤健太追加

# FT税抜: 419,600 + 遠藤17,000(税抜) = 436,600
ft_zeinuki_7 = ft_zeinuki_6 + 17000
ft_zeikomi_7 = int(ft_zeinuki_7 * 1.1)
print(f"  TERRA: 6月と同(税込{terra_zeikomi_6:,}-源泉{terra_gensen_6:,}={terra_jissyu_6:,}円)", flush=True)
print(f"  GL: 税込{gl_zeikomi_6:,}円", flush=True)
print(f"  FT: 税抜{ft_zeinuki_7:,}→税込{ft_zeikomi_7:,}円（遠藤追加+18,700）", flush=True)
print(f"  鶴見(8月稼働→9月末): 税込{tsurumi_zeikomi_8:,}円", flush=True)

# 岡本払出（7月稼働: 6月稼働分 + 遠藤17,000円÷2=8,500円）
# 遠藤は岡本折半なので半分払出
okamoto_7_excluded = 118400 + 8500  # 遠藤折半分追加
okamoto_7_included = int(okamoto_7_excluded * 1.1)
print(f"  岡本払出(7月稼働): 税抜{okamoto_7_excluded:,}→税込{okamoto_7_included:,}円（遠藤折半+8,500税抜）", flush=True)
print(f"  岡本払出(鶴見8月分): 税込{tsurumi_okamoto_8:,}円", flush=True)
print(f"  木原さん分: 税込{kihara_8:,}円", flush=True)

sep_tedori = (
    terra_jissyu_6 + gl_zeikomi_6 + ft_zeikomi_7 + tsurumi_zeikomi_8 - okamoto_7_included - tsurumi_okamoto_8 - kihara_8
)
sep_gengaku = sep_tedori + terra_gensen_6
print(f"  ★手取り: {sep_tedori:,}円", flush=True)
print(f"  TERRA源泉: +{terra_gensen_6:,}円", flush=True)
print(f"  ★額面: {sep_gengaku:,}円", flush=True)

print("\n" + "=" * 70, flush=True)
print("【最終サマリー】", flush=True)
print("=" * 70, flush=True)
print(f"\n{'月':<8}{'手取り(税込)':>15}{'TERRA源泉':>14}{'額面(源泉込)':>15}", flush=True)
print("-" * 55, flush=True)
print(f"6月入金{'':<3}{june_tedori:>14,}円{june_gensen:>12,}円{june_gengaku:>13,}円", flush=True)
print(f"7月入金{'':<3}{july_tedori:>14,}円{terra_gensen_5:>12,}円{july_gengaku:>13,}円", flush=True)
print(f"8月入金{'':<3}{aug_tedori:>14,}円{terra_gensen_6:>12,}円{aug_gengaku:>13,}円", flush=True)
print(f"9月入金{'':<3}{sep_tedori:>14,}円{terra_gensen_6:>12,}円{sep_gengaku:>13,}円", flush=True)
