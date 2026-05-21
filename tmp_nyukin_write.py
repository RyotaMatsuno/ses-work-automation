import sys, openpyxl
sys.stdout.reconfigure(encoding='utf-8')

EXCEL_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\contract\契約マスター_v6.xlsx"
wb = openpyxl.load_workbook(EXCEL_PATH)
ws = wb["入金予測"]

# =======================
# 5月稼働分の確定値
# =======================
# TERRA: site<=45 = 1,633,000(税抜) / site>45 = 120,000(税抜)
terra_45     = 1633000
terra_45_src = int(terra_45 * 0.1021)   # 166,729
terra_45_inc = int(terra_45 * 1.1)       # 1,796,300
terra_45_net = terra_45_inc - terra_45_src  # 1,629,571

terra_60     = 120000
terra_60_src = 12252
terra_60_inc = 132000
terra_60_net = 119748

# GL: 石崎=30日, 山内+荒井=45日
gl_30_inc = 26400   # 石崎 24,000×1.1
gl_45_inc = 92400   # (山内42,000+荒井42,000)×1.1

# FT: 全員45日 416,000×1.1
ft_inc = 457600

# 岡本払出: 橋本奈緒(岡本折半)=47,600÷2=23,800
okamoto = 23800

# 木原さん分: 山内10,000+荒井10,000=20,000(税込22,000)
kihara = 22000

# =======================
# 既存行の書き換え
# =======================
# 現在の構造（0-indexed行番号）:
# 行3: ◆ 2026年6月 入金分
# 行4: 2026/06/30 / 5月稼働分 / TERRA / 源泉 / 税込 / 実入り / GL / FT / 岡本 / 木原 / 総実入り
# 行5: 6月 小計
# 行6: ◆ 2026年7月 入金分
# 行7: 2026/07/15 / 5月稼働分
# 行8: 2026/07/31 / 6月稼働分 → ここは5月稼働分60日に変更
# 行9: 7月 小計

# --- 行4: 6/30 GL 30日分（5月稼働分） ---
# col: A=入金日, B=稼働月, C=TERRA税抜, D=源泉, E=税込, F=実入り, G=GL税込, H=FT税込, I=岡本, J=木原, K=総実入り
r4 = ws[5]  # Excel行5 = 0-indexで行4
ws.cell(row=5, column=1).value = "2026/06/30"
ws.cell(row=5, column=2).value = "5月稼働分"
ws.cell(row=5, column=3).value = "-"
ws.cell(row=5, column=4).value = "-"
ws.cell(row=5, column=5).value = "-"
ws.cell(row=5, column=6).value = "-"
ws.cell(row=5, column=7).value = gl_30_inc   # 26,400
ws.cell(row=5, column=8).value = "-"
ws.cell(row=5, column=9).value = "-"
ws.cell(row=5, column=10).value = "-"
ws.cell(row=5, column=11).value = gl_30_inc  # 総実入り

# --- 行7 (Excel行8): 7/15 TERRA45日+GL45日+FT ---
ws.cell(row=8, column=1).value = "2026/07/15"
ws.cell(row=8, column=2).value = "5月稼働分"
ws.cell(row=8, column=3).value = terra_45         # 1,633,000
ws.cell(row=8, column=4).value = terra_45_src     # 166,729
ws.cell(row=8, column=5).value = terra_45_inc     # 1,796,300
ws.cell(row=8, column=6).value = terra_45_net     # 1,629,571
ws.cell(row=8, column=7).value = gl_45_inc        # 92,400
ws.cell(row=8, column=8).value = ft_inc           # 457,600
ws.cell(row=8, column=9).value = okamoto          # 23,800
ws.cell(row=8, column=10).value = kihara          # 22,000
ws.cell(row=8, column=11).value = terra_45_net + gl_45_inc + ft_inc - okamoto - kihara

# --- 行8 (Excel行9): 7/31 TERRA60日 (5月稼働分) ---
ws.cell(row=9, column=1).value = "2026/07/31"
ws.cell(row=9, column=2).value = "5月稼働分"
ws.cell(row=9, column=3).value = terra_60         # 120,000
ws.cell(row=9, column=4).value = terra_60_src     # 12,252
ws.cell(row=9, column=5).value = terra_60_inc     # 132,000
ws.cell(row=9, column=6).value = terra_60_net     # 119,748
ws.cell(row=9, column=7).value = "-"
ws.cell(row=9, column=8).value = "-"
ws.cell(row=9, column=9).value = "-"
ws.cell(row=9, column=10).value = "-"
ws.cell(row=9, column=11).value = terra_60_net

# 4月稼働分（請求書発行済）セクションを行3の前に挿入
# ◆ 4月稼働分（INV-99〜103発行済み）コメントを行3に追記
ws.cell(row=4, column=1).value = "◆ 2026年6月 入金分（4月稼働分・発行済）"

# 行4に4月分のデータを追加（既存行4=行5の前に1行挿入）
ws.insert_rows(5, amount=3)

# 4月稼働分 入金 (INV-102 GL30日)
ws.cell(row=5, column=1).value = "2026/06/01"
ws.cell(row=5, column=2).value = "4月稼働分"
ws.cell(row=5, column=3).value = "-"
ws.cell(row=5, column=4).value = "-"
ws.cell(row=5, column=5).value = "-"
ws.cell(row=5, column=6).value = "-"
ws.cell(row=5, column=7).value = 46200   # GL30日 42,000×1.1
ws.cell(row=5, column=8).value = "-"
ws.cell(row=5, column=9).value = "-"
ws.cell(row=5, column=10).value = "-"
ws.cell(row=5, column=11).value = 46200

# 4月稼働分 入金 (INV-99 TERRA45日 / INV-101 FT45日 / INV-103 GL45日)
terra4_45 = 326810
terra4_45_src = int(terra4_45 * 0.1021)  # 33,387
terra4_45_inc = int(terra4_45 * 1.1)     # 359,491
terra4_45_net = terra4_45_inc - terra4_45_src  # 326,104
ws.cell(row=6, column=1).value = "2026/06/15"
ws.cell(row=6, column=2).value = "4月稼働分"
ws.cell(row=6, column=3).value = terra4_45
ws.cell(row=6, column=4).value = terra4_45_src
ws.cell(row=6, column=5).value = terra4_45_inc
ws.cell(row=6, column=6).value = terra4_45_net
ws.cell(row=6, column=7).value = 92400   # GL45日 84,000×1.1
ws.cell(row=6, column=8).value = 431200  # FT45日 392,000×1.1
ws.cell(row=6, column=9).value = "-"
ws.cell(row=6, column=10).value = "-"
ws.cell(row=6, column=11).value = terra4_45_net + 92400 + 431200

# 4月稼働分 入金 (INV-100 TERRA60日)
terra4_60 = 120000
terra4_60_src = 12252
terra4_60_inc = 132000
terra4_60_net = 119748
ws.cell(row=7, column=1).value = "2026/06/30"
ws.cell(row=7, column=2).value = "4月稼働分"
ws.cell(row=7, column=3).value = terra4_60
ws.cell(row=7, column=4).value = terra4_60_src
ws.cell(row=7, column=5).value = terra4_60_inc
ws.cell(row=7, column=6).value = terra4_60_net
ws.cell(row=7, column=7).value = "-"
ws.cell(row=7, column=8).value = "-"
ws.cell(row=7, column=9).value = "-"
ws.cell(row=7, column=10).value = "-"
ws.cell(row=7, column=11).value = terra4_60_net

wb.save(EXCEL_PATH)

print("=== 入金予測 更新完了 ===")
print()
print("[4月稼働分 入金]")
print(f"  6/01: GL 30日     46,200円（石崎、税込）")
print(f"  6/15: TERRA {terra4_45:,}円（税抜）→源泉{terra4_45_src:,} 実入{terra4_45_net:,}")
print(f"        GL 45日     92,400円（山内+荒井、税込）")
print(f"        FT          431,200円（税込）")
print(f"        小計: {terra4_45_net + 92400 + 431200:,}円")
print(f"  6/30: TERRA {terra4_60:,}円（税抜）→実入{terra4_60_net:,}")
print()
print("[5月稼働分 入金]")
print(f"  6/30: GL 30日     {gl_30_inc:,}円（石崎、税込）")
print(f"  7/15: TERRA {terra_45:,}円（税抜）→源泉{terra_45_src:,} 実入{terra_45_net:,}")
print(f"        GL 45日     {gl_45_inc:,}円（山内+荒井、税込）")
print(f"        FT          {ft_inc:,}円（税込）")
print(f"        岡本払出    -{okamoto:,}円")
print(f"        木原さん    -{kihara:,}円")
print(f"        小計: {terra_45_net + gl_45_inc + ft_inc - okamoto - kihara:,}円")
print(f"  7/31: TERRA {terra_60:,}円（税抜）→実入{terra_60_net:,}")
