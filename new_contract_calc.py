import math, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 70)
print("■ 新規契約（TERRA岡本担当BP）試算")
print("=" * 70)

print("""
【案件情報】
  案件名: アルコール飲料の製造販売会社のシステム開発
  現場: 田町駅
  入場日: 7月1日（仮）
  精算: 140-180h
  
【単価構造】
  上位単価(案件): 800,000円
  仕入単価(下位): 750,000円
  粗利: 50,000円
  
【請求ルール: TERRA岡本担当BP】
  TERRA請求 = 粗利×80% = 40,000円(税抜)
  岡本払出 = TERRA請求×70% = 28,000円(税抜)
  松野実入り = TERRA請求×30% = 12,000円(税抜)
""")

# 入金タイミング（サイト45想定）
print("【入金タイミング(サイト45想定)】")
print("  7月稼働 → 9月15日初回入金")
print()

# 9月への影響
print("=" * 70)
print("■ 9月総実入り（新規追加後）")
print("=" * 70)

# Current 9月 values
tr_req_old = 480000
tr_15_old = 360000
tr_m_old = 120000

# Add new contract to 15日 (site45)
tr_15_new = tr_15_old + 40000
tr_m_new = tr_m_old  # unchanged
tr_req_new = tr_15_new + tr_m_new  # 520,000

gen15 = math.floor(tr_15_new * 0.1021)
tzei15 = int(tr_15_new * 1.1)
tri15 = tzei15 - gen15

genm = math.floor(tr_m_new * 0.1021)
tzeim = int(tr_m_new * 1.1)
trim = tzeim - genm

tr_ri_new = tri15 + trim
gen_total = gen15 + genm

gl_incl = int(108000 * 1.1)
ft_incl = int(429600 * 1.1)
choku = 107800

# 岡本 (old + new 28k)
oka_terra = 47000 + 28000  # 既存47k + 新規28k
oka_ft = 17000 + 47600 + 17000  # 橋本+鶴川+遠藤
oka_choku = 50000
oka_total = oka_terra + oka_ft + oka_choku

kihara = 96000

sou = tr_ri_new + gl_incl + ft_incl + choku - oka_total - kihara
sou_before_gensen = sou + gen_total

print(f"\n  TERRA請求(税抜)   {tr_req_new:>10,}  ← 旧{tr_req_old:,} + 新規40,000")
print(f"  源泉徴収         △{gen_total:>9,}")
print(f"  TERRA税込         {tzei15+tzeim:>10,}")
print(f"  TERRA実入り       {tr_ri_new:>10,}")
print(f"  GL(税抜)×1.1       {gl_incl:>10,}  (税込)")
print(f"  FT(税抜)×1.1       {ft_incl:>10,}  (税込)")
print(f"  直契約(税込)       {choku:>10,}")
print(f"  ─────────────────────────────────")
print(f"  収入合計          {tr_ri_new+gl_incl+ft_incl+choku:>10,}")
print(f"")
print(f"  岡本(税抜)")
print(f"    TERRA: 既存47k+新規28k     △{oka_terra:>7,}")
print(f"    FT: 橋本17k+鶴川47.6k+遠藤17k  △{oka_ft:>7,}")
print(f"    鶴見:                       △{oka_choku:>7,}")
print(f"                              △{oka_total:>10,}")
print(f"  木原(税抜)                   △{kihara:>10,}")
print(f"  ─────────────────────────────────")
print(f"  ■ 総実入り(源泉後)   {sou:>10,}")
print(f"  ■ 額面(源泉前)       {sou_before_gensen:>10,}")

print(f"\n  ※前回比: 903,552 → {sou:,} (+{sou-903552:,})")
print(f"  ※源泉前: 952,560 → {sou_before_gensen:,} (+{sou_before_gensen-952560:,})")

# 全月比較
print(f"\n{'='*70}")
print(f"■ 新規追加後の月別推移")
print(f"{'='*70}")
print(f"  {'月':>4} | {'総実入(源泉後)':>14} | {'額面(源泉前)':>12} | 備考")
print(f"  {'-'*60}")

months = [
    ('6月', 823066, 823066+45434, ''),
    ('7月', 874295, 874295+44836, '鶴見初回'),
    ('8月', 843237, 843237+44923, '吉田祥平入場'),
    ('9月', sou, sou_before_gensen, '佐藤+稲葉+遠藤+★新規BP'),
    ('10月', 0, 0, '永野安江退場+佐々木BP退場'),
]

# 10月計算 (August work)
# 片山 still active, 永野/安江/佐々木BP gone, new BP still active
tr15_oct = (150000  # 10P: 仲山,蒲池,白須,片山,赤木,日比野,相川,富永,橋詰,齋藤
           + 45000+30000+40000+25000+40000)  # BPs: 芹澤,小山内,吉田祥平T,佐藤礼奈,新規BP
trm_oct = 120000  # 8人(稲葉still active Aug)
g15o = math.floor(tr15_oct*0.1021); t15o = int(tr15_oct*1.1); r15o = t15o-g15o
gmo = math.floor(trm_oct*0.1021); tmo = int(trm_oct*1.1); rmo = tmo-gmo
oka_oct = (47000-20000+28000) + 81600 + 50000  # TERRA:齋藤9k+天野9k+岩瀬9k+新規28k(佐々木20k退場), FT, 鶴見
sou_oct = r15o+rmo + gl_incl + ft_incl + choku - oka_oct - kihara
gen_oct = g15o+gmo

months[4] = ('10月', sou_oct, sou_oct+gen_oct, '永野安江+佐々木退場/片山・新規BP残')

for mo, s, sb, note in months:
    print(f"  {mo:>4} | {s:>14,} | {sb:>12,} | {note}")

print(f"\n  100万まで残り(9月): {1000000-sou:,}（源泉後）/ {1000000-sou_before_gensen:,}（源泉前）")
