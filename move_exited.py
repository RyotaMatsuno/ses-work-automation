import gspread, sys, io, time
from google.oauth2.service_account import Credentials

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')

# ============================================================
# Step 1: Create 退場済み sheet
# ============================================================
try:
    taijo = sh.worksheet('退場済み')
    print("[EXISTS] 退場済みシート既存")
except:
    taijo = sh.add_worksheet(title='退場済み', rows=100, cols=25)
    print("[CREATED] 退場済みシート作成")

# ============================================================
# Step 2: Identify exited engineers in each sheet
# ============================================================
# TERRA: status column = index 2
terra = sh.worksheet('TERRA')
t_all = terra.get_all_values()
t_header = t_all[3]  # Row 4 = header

# FT: status column = index 1
ft = sh.worksheet('フラップテック')
f_all = ft.get_all_values()
f_header = f_all[1]  # Row 2 = header (Row 1 is title, Row 2 is empty/header area)

# GL: status column = index 0
gl = sh.worksheet('グレイスライン')
g_all = gl.get_all_values()
g_header = g_all[1]  # Row 2 = header

# Check which rows are exited
def is_exited(status):
    s = status.strip()
    return '退場' in s or '終了' in s

# TERRA exited rows (data starts Row 5 = index 4)
terra_exited = []
for i in range(4, len(t_all)):
    r = t_all[i]
    if len(r) > 3 and r[3] and is_exited(r[2]):
        terra_exited.append((i+1, r[3], r[2], r))  # (row_num, name, status, data)

# FT exited rows (data starts Row 4 = index 3)
ft_exited = []
for i in range(3, len(f_all)):
    r = f_all[i]
    if len(r) > 2 and r[2] and is_exited(r[1]):
        ft_exited.append((i+1, r[2], r[1], r))

# GL exited rows (data starts Row 4 = index 3)
gl_exited = []
for i in range(3, len(g_all)):
    r = g_all[i]
    if len(r) > 1 and r[1] and is_exited(r[0]):
        gl_exited.append((i+1, r[1], r[0], r))

print(f"\n=== 退場対象 ===")
print(f"TERRA ({len(terra_exited)}名):")
for row, name, status, _ in terra_exited:
    print(f"  Row{row}: {name} [{status}]")

print(f"\nFT ({len(ft_exited)}名):")
for row, name, status, _ in ft_exited:
    print(f"  Row{row}: {name} [{status}]")

print(f"\nGL ({len(gl_exited)}名):")
for row, name, status, _ in gl_exited:
    print(f"  Row{row}: {name} [{status}]")

# ============================================================
# Step 3: Write to 退場済み sheet
# ============================================================
# Format: 元シート | (original columns)
write_rows = []

# Header row
write_rows.append(['元シート'] + t_header)  # Use TERRA header as base (longest)
taijo_row = 1

# TERRA exited
for _, name, status, data in terra_exited:
    padded = data + [''] * (len(t_header) - len(data))
    write_rows.append(['TERRA'] + padded)

# FT exited  
for _, name, status, data in ft_exited:
    padded = data + [''] * (len(t_header) - len(data))
    write_rows.append(['FT'] + padded)

# GL exited
for _, name, status, data in gl_exited:
    padded = data + [''] * (len(t_header) - len(data))
    write_rows.append(['GL'] + padded)

if write_rows:
    taijo.update(f'A1:Z{len(write_rows)}', write_rows, value_input_option='RAW')
    print(f"\n[OK] 退場済みシートに {len(write_rows)-1} 名を書き込み")

# ============================================================
# Step 4: Delete exited rows from original sheets (reverse order)
# ============================================================
# TERRA
for row, name, status, _ in sorted(terra_exited, key=lambda x: x[0], reverse=True):
    terra.delete_rows(row)
    print(f"  TERRA Row{row} {name} 削除")
time.sleep(1)

# FT
for row, name, status, _ in sorted(ft_exited, key=lambda x: x[0], reverse=True):
    ft.delete_rows(row)
    print(f"  FT Row{row} {name} 削除")
time.sleep(1)

# GL
for row, name, status, _ in sorted(gl_exited, key=lambda x: x[0], reverse=True):
    gl.delete_rows(row)
    print(f"  GL Row{row} {name} 削除")

print("\n=== 完了 ===")
print(f"退場済みシートに移動: TERRA {len(terra_exited)}名, FT {len(ft_exited)}名, GL {len(gl_exited)}名")
print("今後は請求書送付後に退場済みシートへ移動する運用でOK")
