import gspread
from google.oauth2.service_account import Credentials
import math

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')

# ============================================================
# 1) TERRA worksheet: Insert 稲葉元希 at Row 37 (before 稼働中合計)
# ============================================================
terra = sh.worksheet('TERRA')

# Column order (from header Row 4):
# A:担当 B:区分 C:ステータス D:氏名 E:参画時期 F:期間 G:案件/上位会社
# H:単価(案件) I:支払サイト J:勤怠表フロー K:更新サイクル L:業務内容
# M:仕入先(所属) N:仕入単価 O:粗利 P:TERRA請求額 Q:岡本払出 R:実入り
# S:備考 T:2026年7月_稼働確定 U:契約区分

new_row = [
    '',            # A: 担当 (空白=松野)
    'P',           # B: 区分
    '入場前',       # C: ステータス
    '稲葉元希',     # D: 氏名
    '2026/7',      # E: 参画時期
    '9月末終了',    # F: 期間
    '（確認中）',   # G: 案件/上位会社
    '350000',      # H: 単価(案件)
    '60',          # I: 支払サイト
    '',            # J: 勤怠表フロー
    '3か月',       # K: 更新サイクル
    '',            # L: 業務内容
    'TERRA',       # M: 仕入先(所属)
    '',            # N: 仕入単価
    '',            # O: 粗利
    '15000',       # P: TERRA請求額
    '',            # Q: 岡本払出
    '',            # R: 実入り
    '準委任・固定精算・7/6入場',  # S: 備考
    '',            # T: 2026年7月_稼働確定
    '準委任',      # U: 契約区分
]

# Insert row before 稼働中合計 (currently Row 37)
terra.insert_row(new_row, index=37)
print("[OK] TERRA: 稲葉元希を Row 37 に挿入完了")

# ============================================================
# 2) 入金予測 worksheet: Update affected rows
# ============================================================
yosoku = sh.worksheet('入金予測')

# 稲葉元希: TERRA請求額 15,000/月, 60日サイト, 7-9月稼働
# 60日サイト = 当月末締め翌々月末日払い
#   7月work → 9月30日入金 (Row 21)
#   8月work → 10月31日入金 (Row 26)
#   9月work → 11月30日入金 (Row 31)
#
# 現在の末日行: TERRA請求=105,000 → 新: 120,000
# 更新対象: 末日行(C-F列,K列) + 小計行(C-F列,K列) + 年間合計(Row 64)

def calc_terra(terra_zeinuki):
    """TERRA系の計算"""
    gensen = math.floor(terra_zeinuki * 0.1021)
    zeikomi = terra_zeinuki * 1.1
    jitsuiri = zeikomi - gensen
    return int(gensen), int(zeikomi), int(jitsuiri)

# 新しい末日行の値
new_matsu_terra = 120000  # 105000 + 15000
g, z, j = calc_terra(new_matsu_terra)
print(f"  末日行: TERRA請求={new_matsu_terra}, 源泉={g}, 税込={z}, 実入り={j}")

# 末日行のGL='-', FT=20400, 岡本=-18000, 木原='-' → 変化なし
# 総実入り = TERRA実入り + 0 + 20400 + (-18000) + 0
new_matsu_sou = j + 0 + 20400 + (-18000) + 0
print(f"  末日行 総実入り: {new_matsu_sou}")

# 更新する末日行: Row 21(9月), Row 26(10月), Row 31(11月)
matsu_rows = [21, 26, 31]
for row_num in matsu_rows:
    # C列=TERRA請求, D列=源泉, E列=税込, F列=実入り (1-indexed: C=3, D=4, E=5, F=6)
    yosoku.update_cell(row_num, 3, new_matsu_terra)
    yosoku.update_cell(row_num, 4, g)
    yosoku.update_cell(row_num, 5, z)
    yosoku.update_cell(row_num, 6, j)
    # K列=総実入り (K=11)
    yosoku.update_cell(row_num, 11, new_matsu_sou)
    print(f"[OK] 入金予測: Row {row_num} 末日行を更新")

# 小計行の更新: Row 22(9月), Row 27(10月), Row 32(11月)
# 小計 = 15日行 + 末日行
# 15日行は変化なし: TERRA請求=380000, 源泉=38798, 税込=418000, 実入り=379202
shoukei_rows = [22, 27, 32]
for row_num in shoukei_rows:
    # 15日行は直前行を参照(変化なし)
    ju5_row = yosoku.row_values(row_num - 2)  # 15日行
    
    # 15日行の値を取得
    ju5_terra = int(ju5_row[2]) if ju5_row[2] else 0
    ju5_gensen = int(ju5_row[3]) if ju5_row[3] else 0
    ju5_zeikomi = int(ju5_row[4]) if ju5_row[4] else 0
    ju5_jitsuiri = int(ju5_row[5]) if ju5_row[5] else 0
    
    # GL列(7), FT列(8), 岡本列(9), 木原列(10)
    def parse_val(v):
        if not v or v == '-':
            return 0
        return int(v.replace(',', ''))
    
    ju5_gl = parse_val(ju5_row[6])
    ju5_ft = parse_val(ju5_row[7])
    ju5_oka = parse_val(ju5_row[8])
    ju5_ki = parse_val(ju5_row[9])
    
    # 末日行の非TERRA値(変化なし)
    matsu_gl = 0     # '-'
    matsu_ft = 20400
    matsu_oka = -18000
    matsu_ki = 0     # '-'
    
    # 小計を計算
    s_terra = ju5_terra + new_matsu_terra
    s_gensen = ju5_gensen + g
    s_zeikomi = ju5_zeikomi + z
    s_jitsuiri = ju5_jitsuiri + j
    s_gl = ju5_gl + matsu_gl
    s_ft = ju5_ft + matsu_ft
    s_oka = ju5_oka + matsu_oka
    s_ki = ju5_ki + matsu_ki
    s_sou = s_jitsuiri + s_gl + s_ft + s_oka + s_ki
    
    yosoku.update_cell(row_num, 3, s_terra)
    yosoku.update_cell(row_num, 4, s_gensen)
    yosoku.update_cell(row_num, 5, s_zeikomi)
    yosoku.update_cell(row_num, 6, s_jitsuiri)
    yosoku.update_cell(row_num, 11, s_sou)
    print(f"[OK] 入金予測: Row {row_num} 小計行を更新 (TERRA請求={s_terra}, 総実入り={s_sou})")

# 年間総合計 (Row 64 → insert_rowでTERRAが1行ずれないので入金予測は別シート、影響なし)
# 年間合計を全小計行から再計算
print("\n--- 年間合計の再計算 ---")
# 小計行のリスト: Row 7,12,17,22,27,32,37,42,47,52,57,62
shoukei_all = [7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
totals = [0] * 9  # C~K (index 0=TERRA請求 ~ 8=総実入り)

for sr in shoukei_all:
    row_data = yosoku.row_values(sr)
    for idx in range(9):
        col_val = row_data[2 + idx] if len(row_data) > (2 + idx) else '0'
        totals[idx] += parse_val(col_val)

# Row 64 に書き込み
for idx in range(9):
    yosoku.update_cell(64, 3 + idx, totals[idx])

print(f"[OK] 入金予測: Row 64 年間合計を更新")
print(f"  TERRA請求={totals[0]}, 源泉={totals[1]}, 税込={totals[2]}, 実入り={totals[3]}")
print(f"  GL={totals[4]}, FT={totals[5]}, 岡本={totals[6]}, 木原={totals[7]}, 総実入り={totals[8]}")
print("\n=== 全更新完了 ===")
