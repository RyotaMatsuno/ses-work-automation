import gspread, sys, io
from google.oauth2.service_account import Credentials

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')
yosoku = sh.worksheet('入金予測')

def pv(v):
    if not v or v == '-' or v.strip() == '':
        return 0
    return int(str(v).replace(',',''))

sub_rows = [7,12,17,22,27,32,37,42,47,52,57,62]
months = ['6月','7月','8月','9月','10月','11月','12月','1月','2月','3月','4月','5月']

print(f"{'月':>4} | {'TR実入':>8} | {'GL':>7} | {'FT':>7} | {'直契約':>7} | {'岡本':>8} | {'木原':>7} | {'総実入り':>9} | 検算")
print("-" * 90)

ann = [0]*6
ann_sou = 0
for sr, mo in zip(sub_rows, months):
    row = yosoku.row_values(sr)
    tr_ri = pv(row[5])
    gl    = pv(row[6])
    ft    = pv(row[7])
    choku = pv(row[8])
    oka   = pv(row[9])
    ki    = pv(row[10])
    sou   = pv(row[11])
    
    check = tr_ri + gl + ft + choku + oka + ki
    ok = 'OK' if check == sou else f'NG({check})'
    
    print(f"{mo:>4} | {tr_ri:>8,} | {gl:>7,} | {ft:>7,} | {choku:>7,} | {oka:>8,} | {ki:>7,} | {sou:>9,} | {ok}")
    ann[0]+=tr_ri; ann[1]+=gl; ann[2]+=ft; ann[3]+=choku; ann[4]+=oka; ann[5]+=ki
    ann_sou += sou

print("-" * 90)
print(f"年間 | {ann[0]:>8,} | {ann[1]:>7,} | {ann[2]:>7,} | {ann[3]:>7,} | {ann[4]:>8,} | {ann[5]:>7,} | {ann_sou:>9,} |")
print(f"\n月平均実入り: {ann_sou//12:,}")
print(f"9月以降安定月(9-11月): {818045:,}/月")
