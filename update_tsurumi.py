import gspread
from google.oauth2.service_account import Credentials
import math, time

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')
yosoku = sh.worksheet('\u5165\u91d1\u4e88\u6e2c')

# ============================================
# Step 0: Read all current data
# ============================================
all_data = yosoku.get_all_values()
print(f"Read {len(all_data)} rows, {len(all_data[0])} cols")
print(f"Sheet ID: {yosoku.id}")

# Current columns (0-indexed):
# 0:入金予定日 1:稼働月 2:TERRA請求 3:源泉 4:TERRA税込 5:TERRA実入り
# 6:GL税込 7:FT税込 8:岡本払出 9:木原さん分 10:総実入り

# ============================================
# Step 1: Insert blank column at position I (index 8, 1-indexed=9)
#   → 直契約(税込) column
#   Old I(岡本)→J, J(木原)→K, K(総実入り)→L
# ============================================
body = {
    'requests': [{
        'insertDimension': {
            'range': {
                'sheetId': yosoku.id,
                'dimension': 'COLUMNS',
                'startIndex': 8,
                'endIndex': 9
            },
            'inheritFromBefore': True
        }
    }]
}
sh.batch_update(body)
print("[OK] Column I inserted (直契約)")
time.sleep(1)

# After insert, columns are (0-indexed):
# 0:入金予定日 1:稼働月 2:TERRA請求 3:源泉 4:TERRA税込 5:TERRA実入り
# 6:GL税込 7:FT税込 8:直契約(NEW) 9:岡本払出 10:木原さん分 11:総実入り

# ============================================
# Step 2: Prepare all cell updates
# ============================================
def pv(v):
    """Parse value - handle '-', empty, commas"""
    if not v or v == '-' or v.strip() == '':
        return 0
    return int(str(v).replace(',', '').replace('\\-', '-').replace('\u2212', '-'))

# Re-read after column insert
time.sleep(1)
all_data = yosoku.get_all_values()
print(f"After insert: {len(all_data)} rows, {len(all_data[0])} cols")

# Row mapping:
# 15日 rows: 5,10,15,20,25,30,35,40,45,50,55,60
# 末日 rows: 6,11,16,21,26,31,36,41,46,51,56,61
# 小計 rows: 7,12,17,22,27,32,37,42,47,52,57,62
# 空白 rows: 8,13,18,23,28,33,38,43,48,53,58,63
# section header rows: 4,9,14,19,24,29,34,39,44,49,54,59
# annual total: 64

# 鶴見: 10万(税抜) x 1.1 = 110,000(税込), 翌月末日払い, 6月稼働開始
# → 7月末(Row11)から毎月末日に入金
# 岡本払出: 5万/月追加

TSURUMI_ZEIKOMI = 110000
TSURUMI_OKAMOTO = -50000

# 鶴見の対象末日行 (7月末以降)
tsurumi_matsu = [11, 16, 21, 26, 31, 36, 41, 46, 51, 56, 61]
# June末日 (Row 6) は対象外

batch_cells = []

# --- Header ---
batch_cells.append(gspread.Cell(3, 9, '\u76f4\u5951\u7d04\n(\u7a0e\u8fbc)'))  # 直契約(税込)

# --- 15日 rows: set '-' for 直契約 column ---
for r in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]:
    batch_cells.append(gspread.Cell(r, 9, '-'))

# --- June末日 (Row 6): no 鶴見 ---
batch_cells.append(gspread.Cell(6, 9, '-'))

# --- 末日 rows from July: 直契約 = 110,000, 岡本 += -50,000 ---
for r in tsurumi_matsu:
    # 直契約 column (col 9)
    batch_cells.append(gspread.Cell(r, 9, TSURUMI_ZEIKOMI))
    
    # 岡本 column (col 10) - read current and add
    row_data = all_data[r - 1]
    old_oka = pv(row_data[9]) if len(row_data) > 9 else 0  # col 10 = index 9 (after insert, old 岡本 shifted to index 9)
    # Wait - after the column insert, the data I read should already have the new layout
    # But the re-read might show the old 岡本 value in column 9 (0-indexed)
    # Let me check: after insert at index 8, old column 8 (岡本) is now at index 9
    new_oka = old_oka + TSURUMI_OKAMOTO
    batch_cells.append(gspread.Cell(r, 10, new_oka))

# --- June小計 (Row 7): 直契約 = '-' ---
batch_cells.append(gspread.Cell(7, 9, '-'))

# --- 小計 rows from July: recalculate ---
shoukei_rows = [12, 17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
for r in shoukei_rows:
    # 直契約: 15日('-') + 末日(110000) = 110000
    batch_cells.append(gspread.Cell(r, 9, TSURUMI_ZEIKOMI))
    
    # 岡本: sum of 15日 + 末日 (both now updated)
    ju5_row = all_data[r - 3]  # 15日 is 2 rows before subtotal
    matsu_row = all_data[r - 2]  # 末日 is 1 row before subtotal
    
    ju5_oka = pv(ju5_row[9]) if len(ju5_row) > 9 else 0
    matsu_oka_old = pv(matsu_row[9]) if len(matsu_row) > 9 else 0
    
    # Check if this month has 鶴見
    matsu_row_num = r - 1
    if matsu_row_num in tsurumi_matsu:
        matsu_oka_new = matsu_oka_old + TSURUMI_OKAMOTO
    else:
        matsu_oka_new = matsu_oka_old
    
    batch_cells.append(gspread.Cell(r, 10, ju5_oka + matsu_oka_new))

# --- 総実入り (col 12) recalculation for ALL data rows ---
# 総実入り = TERRA実入り(6) + GL(7) + FT(8) + 直契約(9) + 岡本(10) + 木原(11)
# But we need the FINAL values, so let's build a dict of updates first

# Create a lookup of pending updates
update_lookup = {}
for cell in batch_cells:
    update_lookup[(cell.row, cell.col)] = cell.value

def get_final_val(row_num, col_1indexed):
    """Get the final value for a cell (either from pending updates or original data)"""
    if (row_num, col_1indexed) in update_lookup:
        v = update_lookup[(row_num, col_1indexed)]
        if v == '-' or v == '':
            return 0
        return int(v)
    else:
        idx = col_1indexed - 1
        row_data = all_data[row_num - 1]
        return pv(row_data[idx]) if len(row_data) > idx else 0

# All rows needing 総実入り recalculation
all_sou_rows = [5, 6, 7, 10, 11, 12, 15, 16, 17, 20, 21, 22, 
                25, 26, 27, 30, 31, 32, 35, 36, 37, 40, 41, 42,
                45, 46, 47, 50, 51, 52, 55, 56, 57, 60, 61, 62]

for r in all_sou_rows:
    terra_jitsuiri = get_final_val(r, 6)  # col F
    gl = get_final_val(r, 7)              # col G
    ft = get_final_val(r, 8)              # col H
    choku = get_final_val(r, 9)           # col I (直契約)
    oka = get_final_val(r, 10)            # col J (岡本)
    ki = get_final_val(r, 11)             # col K (木原)
    
    sou = terra_jitsuiri + gl + ft + choku + oka + ki
    batch_cells.append(gspread.Cell(r, 12, sou))

# --- Section headers and empty rows: set '-' for 直契約 ---
for r in [1, 2, 4, 8, 9, 13, 14, 18, 19, 23, 24, 28, 29, 33, 34, 38, 39, 43, 44, 48, 49, 53, 54, 58, 59, 63]:
    if r <= len(all_data):
        batch_cells.append(gspread.Cell(r, 9, ''))

# --- Annual total (Row 64) ---
shoukei_all = [7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
annual = [0] * 10  # cols C(3) through L(12)
for sr in shoukei_all:
    for idx in range(10):
        col = 3 + idx
        annual[idx] += get_final_val(sr, col)

for idx in range(10):
    batch_cells.append(gspread.Cell(64, 3 + idx, annual[idx]))

# ============================================
# Step 3: Execute batch update
# ============================================
print(f"Batch updating {len(batch_cells)} cells...")
yosoku.update_cells(batch_cells, value_input_option='RAW')
print("[OK] All cells updated")

# ============================================
# Step 4: Print summary
# ============================================
print("\n=== Update Summary ===")
print(f"直契約(税込): {TSURUMI_ZEIKOMI:,}/month (7月末入金~)")
print(f"岡本追加: {TSURUMI_OKAMOTO:,}/month")

# Print updated subtotals
for sr in shoukei_all:
    sou = get_final_val(sr, 12)
    month_label = all_data[sr - 1][0] if len(all_data[sr - 1]) > 0 else f'Row{sr}'
    print(f"  {month_label}: total={sou:,}")

print(f"\nAnnual totals:")
labels = ['TERRA請求', '源泉', 'TERRA税込', 'TERRA実入り', 'GL', 'FT', '直契約', '岡本', '木原', '総実入り']
for i, label in enumerate(labels):
    print(f"  {label}: {annual[i]:,}")

print("\n=== Done ===")
