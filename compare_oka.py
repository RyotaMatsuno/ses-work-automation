import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 9月の総実入り - 鶴川の岡本金額による比較
print("=== 鶴川岡本額による9月の総実入り比較 ===\n")

terra_ri = 478992
gl_incl = 118800
ft_incl = 472560
choku = 107800
kihara = 96000

# TERRA岡本（共通）: 齋藤9k + 佐々木20k + 天野9k + 岩瀬9k = 47,000
terra_oka = 47000
# 直契約岡本（共通）: 鶴見50k
choku_oka = 50000

# パターン1: 鶴川=47,600(全額) + 橋本=17,000
ft_oka_1 = 17000 + 47600 + 17000  # 橋本+鶴川+遠藤
oka_1 = terra_oka + ft_oka_1 + choku_oka
sou_1 = terra_ri + gl_incl + ft_incl + choku - oka_1 - kihara
print(f"① 鶴川=47,600(全額) + 橋本=17,000")
print(f"   岡本合計: {oka_1:,} → 総実入り: {sou_1:,}")

# パターン2: 鶴川=9,520(シート値) + 橋本=17,000
ft_oka_2 = 17000 + 9520 + 17000
oka_2 = terra_oka + ft_oka_2 + choku_oka
sou_2 = terra_ri + gl_incl + ft_incl + choku - oka_2 - kihara
print(f"② 鶴川=9,520(シート値) + 橋本=17,000")
print(f"   岡本合計: {oka_2:,} → 総実入り: {sou_2:,}")

# パターン3: 鶴川=9,520 + 橋本=23,800(旧値)
ft_oka_3 = 23800 + 9520 + 17000
oka_3 = terra_oka + ft_oka_3 + choku_oka
sou_3 = terra_ri + gl_incl + ft_incl + choku - oka_3 - kihara
print(f"③ 鶴川=9,520 + 橋本=23,800(旧arariベース) ← 前回6/16の計算に近い")
print(f"   岡本合計: {oka_3:,} → 総実入り: {sou_3:,}")

print(f"\n差額:")
print(f"  ①→②: 鶴川の差(47,600→9,520) = +{sou_2-sou_1:,}")
print(f"  ②→③: 橋本の差(17,000→23,800) = {sou_3-sou_2:,}")
