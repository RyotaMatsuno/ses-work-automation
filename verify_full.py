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
    return int(str(v).replace(',',''))

# 小計行
sub_rows = [7,12,17,22,27,32,37,42,47,52,57,62]
months = ['6月','7月','8月','9月','10月','11月','12月','1月','2月','3月','4月','5月']

# After col insert: C=TERRA請求, D=源泉, E=TERRA税込, F=TERRA実入り, G=GL, H=FT, I=直契約, J=岡本, K=木原, L=総実入り

print(f"{'月':>4}  {'TR実入':>8}  {'GL':>7}  {'FT':>7}  {'直契約':>7}  {'岡本':>8}  {'木原':>7}  {'総実入り':>9}  {'検算':>9}")
print("-" * 85)

ann_sum = 0
for sr, mo in zip(sub_rows, months):
    row = yosoku.row_values(sr)
    tr_ri = pv(row[5])   # F: TERRA実入り
    gl    = pv(row[6])   # G: GL
    ft    = pv(row[7])   # H: FT
    choku = pv(row[8])   # I: 直契約
    oka   = pv(row[9])   # J: 岡本
    ki    = pv(row[10])  # K: 木原
    sou   = pv(row[11])  # L: 総実入り
    
    check = tr_ri + gl + ft + choku + oka + ki
    ok = '✓' if check == sou else f'!{check}'
    
    print(f"{mo:>4}  {tr_ri:>8,}  {gl:>7,}  {ft:>7,}  {choku:>7,}  {oka:>8,}  {ki:>7,}  {sou:>9,}  {ok}")
    ann_sum += sou

# Annual
print("-" * 85)
row64 = yosoku.row_values(63)
print(f"年間  {pv(row64[5]):>8,}  {pv(row64[6]):>7,}  {pv(row64[7]):>7,}  {pv(row64[8]):>7,}  {pv(row64[9]):>8,}  {pv(row64[10]):>7,}  {pv(row64[11]):>9,}")
print(f"\n月次小計合計: {ann_sum:,}")
print(f"月平均実入り: {ann_sum//12:,}")
