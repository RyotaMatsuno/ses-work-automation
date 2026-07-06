import gspread
from google.oauth2.service_account import Credentials

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')
yosoku = sh.worksheet('\u5165\u91d1\u4e88\u6e2c')

def pv(v):
    if not v or v == '-' or v.strip() == '':
        return 0
    return int(str(v).replace(',', ''))

# Re-read current state (after all previous updates)
all_data = yosoku.get_all_values()
print(f"Current: {len(all_data)} rows, {len(all_data[0])} cols")

# Verify column layout
row3 = all_data[2]
print(f"Headers: {row3}")

# Print all subtotal rows to verify
shoukei_rows = [7, 12, 17, 22, 27, 32, 37, 42, 47, 52, 57, 62]
print("\n=== Monthly subtotals (current sheet values) ===")
for sr in shoukei_rows:
    row = all_data[sr - 1]
    label = row[0]
    print(f"Row {sr} [{label}]:")
    print(f"  TERRA-ri={row[5]}, GL={row[6]}, FT={row[7]}, Choku={row[8]}, Oka={row[9]}, Ki={row[10]}, Sou={row[11]}")
    
    # Recalculate what 総実入り should be
    expected = pv(row[5]) + pv(row[6]) + pv(row[7]) + pv(row[8]) + pv(row[9]) + pv(row[10])
    actual = pv(row[11])
    if expected != actual:
        print(f"  *** MISMATCH: expected={expected:,}, actual={actual:,}, diff={expected-actual:,}")

# Check annual total
print("\n=== Annual total (Row 64) ===")
row64 = all_data[63]
print(f"  {row64[2:]}")

# Recalculate annual total from subtotals
annual = [0] * 10
for sr in shoukei_rows:
    row = all_data[sr - 1]
    for idx in range(10):
        annual[idx] += pv(row[2 + idx])

print(f"\n=== Expected annual totals ===")
labels = ['TERRA-req', 'Gensen', 'TERRA-zei', 'TERRA-ri', 'GL', 'FT', 'Choku', 'Oka', 'Ki', 'Sou']
for i, label in enumerate(labels):
    current = pv(row64[2 + i])
    expected = annual[i]
    marker = '***' if current != expected else 'OK'
    print(f"  {label}: current={current:,}, expected={expected:,} {marker}")
