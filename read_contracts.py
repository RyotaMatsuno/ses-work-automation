import gspread
from google.oauth2.service_account import Credentials

scopes = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(
    r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ses-work-automation-170e12155a49.json',
    scopes=scopes
)
gc = gspread.authorize(creds)
sh = gc.open_by_key('1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI')

# ========== TERRA ==========
terra = sh.worksheet('TERRA')
t_all = terra.get_all_values()
print("=== TERRA (Row 4=header, data from Row 5) ===")
print(f"Header: {t_all[3]}")  # Row 4
for i in range(4, len(t_all)):
    r = t_all[i]
    if len(r) > 3 and r[3]:  # has name
        # cols: 0=担当 1=区分 2=ステータス 3=氏名 4=参画時期 5=期間
        # 6=案件 7=単価 8=サイト 9-11=... 12=仕入先 13=仕入単価 14=粗利
        # 15=TERRA請求 16=岡本払出 17=実入り 18=備考
        name = r[3]
        status = r[2]
        kubun = r[1]
        tanto = r[0]
        start = r[4]
        period = r[5]
        tanaka = r[7] if len(r) > 7 else ''
        site = r[8] if len(r) > 8 else ''
        shiire = r[13] if len(r) > 13 else ''
        arari = r[14] if len(r) > 14 else ''
        terra_req = r[15] if len(r) > 15 else ''
        oka = r[16] if len(r) > 16 else ''
        jitsuiri = r[17] if len(r) > 17 else ''
        print(f"  Row{i+1} [{status}] {name}: kubun={kubun}, tanto={tanto}, start={start}, period={period}, "
              f"tanaka={tanaka}, site={site}, shiire={shiire}, arari={arari}, "
              f"TR_req={terra_req}, oka={oka}, jitsuiri={jitsuiri}")

# ========== FT ==========
print("\n=== FT ===")
ft = sh.worksheet('\u30d5\u30e9\u30c3\u30d7\u30c6\u30c3\u30af')
f_all = ft.get_all_values()
print(f"Header: {f_all[0]}")  # Row 1 header
for i in range(1, len(f_all)):
    r = f_all[i]
    if len(r) > 2 and r[2]:  # has name (col C)
        name = r[2]
        status = r[1]
        tanto = r[0]
        start = r[3] if len(r) > 3 else ''
        period = r[4] if len(r) > 4 else ''
        tanaka = r[6] if len(r) > 6 else ''
        shiire = r[7] if len(r) > 7 else ''
        arari = r[8] if len(r) > 8 else ''
        ft_req = r[9] if len(r) > 9 else ''
        oka = r[10] if len(r) > 10 else ''
        jitsuiri = r[11] if len(r) > 11 else ''
        site = r[12] if len(r) > 12 else ''
        kihara = r[15] if len(r) > 15 else ''
        print(f"  Row{i+1} [{status}] {name}: tanto={tanto}, start={start}, period={period}, "
              f"tanaka={tanaka}, shiire={shiire}, arari={arari}, "
              f"FT_req={ft_req}, oka={oka}, jitsuiri={jitsuiri}, site={site}, kihara={kihara}")

# ========== GL ==========
print("\n=== GL ===")
gl = sh.worksheet('\u30b0\u30ec\u30a4\u30b9\u30e9\u30a4\u30f3')
g_all = gl.get_all_values()
print(f"Header: {g_all[0]}")
for i in range(1, len(g_all)):
    r = g_all[i]
    if len(r) > 1 and r[1]:  # has name (col B)
        name = r[1]
        status = r[0]
        start = r[2] if len(r) > 2 else ''
        period = r[3] if len(r) > 3 else ''
        tanaka = r[5] if len(r) > 5 else ''
        shiire = r[6] if len(r) > 6 else ''
        arari = r[7] if len(r) > 7 else ''
        gl_req = r[8] if len(r) > 8 else ''
        jitsuiri = r[9] if len(r) > 9 else ''
        site = r[10] if len(r) > 10 else ''
        kihara = r[14] if len(r) > 14 else ''
        print(f"  Row{i+1} [{status}] {name}: start={start}, period={period}, "
              f"tanaka={tanaka}, shiire={shiire}, arari={arari}, "
              f"GL_req={gl_req}, jitsuiri={jitsuiri}, site={site}, kihara={kihara}")
