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

# Re-read ALL worksheets fresh
print("=== TERRA (全行) ===")
terra = sh.worksheet('TERRA')
t_all = terra.get_all_values()
for i in range(4, len(t_all)):
    r = t_all[i]
    if len(r) > 3 and r[3]:
        name = r[3]; status = r[2]; kubun = r[1]; tanto = r[0]
        start = r[4]; period = r[5]; site = r[8] if len(r)>8 else ''
        tr_req = r[15] if len(r)>15 else ''
        oka = r[16] if len(r)>16 else ''
        print(f"  Row{i+1} [{status}] {name} ({kubun}/{tanto}) start={start} period={period} site={site} TR={tr_req} oka={oka}")

print("\n=== FT (全行) ===")
ft = sh.worksheet('フラップテック')
f_all = ft.get_all_values()
for i in range(2, len(f_all)):
    r = f_all[i]
    if len(r) > 2 and r[2]:
        name = r[2]; status = r[1]; tanto = r[0]
        start = r[3] if len(r)>3 else ''; period = r[4] if len(r)>4 else ''
        arari = r[8] if len(r)>8 else ''; ft_req = r[9] if len(r)>9 else ''
        oka = r[10] if len(r)>10 else ''; site = r[12] if len(r)>12 else ''
        kihara = r[15] if len(r)>15 else ''
        print(f"  Row{i+1} [{status}] {name} ({tanto}) start={start} period={period} arari={arari} FT={ft_req} oka={oka} site={site} ki={kihara}")

print("\n=== GL (全行) ===")
gl = sh.worksheet('グレイスライン')
g_all = gl.get_all_values()
for i in range(2, len(g_all)):
    r = g_all[i]
    if len(r) > 1 and r[1]:
        name = r[1]; status = r[0]
        start = r[2] if len(r)>2 else ''; period = r[3] if len(r)>3 else ''
        tanaka = r[5] if len(r)>5 else ''; shiire = r[6] if len(r)>6 else ''
        gl_req = r[8] if len(r)>8 else ''; site = r[10] if len(r)>10 else ''
        kihara = r[14] if len(r)>14 else ''
        print(f"  Row{i+1} [{status}] {name} start={start} period={period} tanaka={tanaka} shiire={shiire} GL={gl_req} site={site} ki={kihara}")
