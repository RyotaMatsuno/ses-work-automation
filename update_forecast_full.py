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
yosoku = sh.worksheet('\u5165\u91d1\u4e88\u6e2c')

# ================================================================
# ALL engineers - payment goes to (work+2)month
# サイト<50 → 15日, サイト>=50 → 末日
# ================================================================
def ym(y,m): return y*100+m

# TERRA: (name, req, is_matsu, start_ym, end_ym, oka)
terra_eng = [
    # P standard (ongoing)
    ('仲山',15000,False, ym(2023,12),None, 0),
    ('吉田創志',15000,True, ym(2024,3),None, 0),   # site50→末日
    ('蒲池',15000,False, ym(2024,3),None, 0),
    ('大野',15000,True, ym(2024,4),None, 0),         # site55
    ('白須',15000,False, ym(2024,5),None, 0),
    ('沼田',15000,True, ym(2024,6),None, 0),         # site55
    ('魚谷',15000,True, ym(2025,4),ym(2026,4), 0),   # 4月終了, site55
    ('片山',15000,False, ym(2025,4),ym(2026,7), 0),   # 7月末終了, site30→15日
    ('赤木',15000,False, ym(2025,7),None, 0),
    ('坪井',15000,True, ym(2025,7),None, 0),         # site50
    ('中村',15000,True, ym(2025,8),None, 0),         # site50
    ('日比野',15000,False, ym(2025,9),None, 0),
    ('永野',15000,False, ym(2025,10),None, 0),
    ('安江',15000,False, ym(2025,10),None, 0),
    ('相川',15000,False, ym(2025,10),None, 0),
    ('富永',15000,False, ym(2026,1),None, 0),
    ('天野',15000,True, ym(2026,1),None, 9000),      # 岡本, site50
    ('岩瀬',15000,True, ym(2026,3),None, 9000),      # 岡本, site50
    ('加藤T',15000,False, ym(2026,3),ym(2026,4), 9000), # 岡本, 退場~April
    ('橋詰',15000,False, ym(2026,4),None, 0),        # site45
    ('齋藤',15000,False, ym(2026,5),None, 9000),      # 岡本, site45
    ('稲葉',15000,True, ym(2026,7),ym(2026,9), 0),   # site60→末日
    # BPs
    ('大本BP',15000,False, ym(2025,9),ym(2026,5), 0),   # 折半 30k×50%=15k, site35
    ('森BP',30000,False, ym(2025,9),ym(2026,5), 0),     # 折半 60k×50%=30k, site40
    ('芹澤BP',45000,False, ym(2025,12),None, 0),        # 折半 90k×50%=45k, site40
    ('小山内BP',30000,False, ym(2026,4),None, 0),        # 折半 60k×50%=30k, site45
    ('佐々木BP',40000,False, ym(2026,4),None, 20000),    # 岡本折半, site45
    ('吉田祥平T',40000,False, ym(2026,6),None, 0),      # BP, TERRA松野のみ, site45
]

# FT: (name, req, is_matsu, start_ym, end_ym, oka, kihara)
ft_eng = [
    ('笠井',68000,False, ym(2026,2),None, 0, 10000),
    ('原FT',68000,False, ym(2026,3),ym(2026,5), 0, 20000),
    ('木村FT',47600,False, ym(2026,3),None, 0, 10000),
    ('加藤小坂',38400,False, ym(2026,3),None, 0, 11000),
    ('川崎FT',27200,False, ym(2026,4),None, 0, 5000),
    ('田中みさFT',20400,True, ym(2026,4),None, 0, 0),    # site55→末日
    ('立野FT',47600,False, ym(2026,4),None, 0, 10000),
    ('佐々木FT',27200,False, ym(2026,4),None, 0, 20000),
    ('橋本FT',47600,False, ym(2026,4),None, 23800, 10000), # 岡本折半 47600/2
    ('鶴川FT',47600,False, ym(2026,5),None, 47600, 0),    # 岡本全額
    ('吉田祥平FT',24000,False, ym(2026,6),None, 0, 0),   # 小坂折半
    ('遠藤FT',34000,False, ym(2026,7),None, 17000, 0),    # 岡本折半 NEW
]

# GL: all 15日, ongoing
GL_TOTAL = 108000  # verified (石崎24k + 山内42k + 荒井42k)
GL_KIHARA = 20000  # 山内10k + 荒井10k

# 鶴見直契約: 2%割引適用
TSURUMI = int(100000 * 0.98 * 1.1)  # 107,800
TSURUMI_OKA = 50000  # flat 5万

# ================================================================
# CALCULATE per payment month
# ================================================================
work_months = [ym(2026,m) for m in range(4,13)] + [ym(2027,m) for m in range(1,4)]
pay_months = [ym(2026,m) for m in range(6,13)] + [ym(2027,m) for m in range(1,6)]

def next2(wm):
    y,m = wm//100, wm%100
    m += 2
    if m > 12: y += 1; m -= 12
    return ym(y,m)

def next1(wm):
    y,m = wm//100, wm%100
    m += 1
    if m > 12: y += 1; m -= 12
    return ym(y,m)

def active(s,e,wm):
    return wm >= s and (e is None or wm <= e)

results = {}
for pm in pay_months:
    results[pm] = {'15': {}, 'matsu': {}}
    for b in ['15','matsu']:
        results[pm][b] = {'terra':0,'ft':0,'gl':0,'choku':0,
                          'oka_terra':0,'oka_ft':0,'oka_choku':0,
                          'kihara_ft':0,'kihara_gl':0}

# TERRA
for name,req,is_matsu,s,e,oka in terra_eng:
    for wm in work_months:
        if not active(s,e,wm):
            continue
        pm = next2(wm)
        if pm not in results:
            continue
        bucket = 'matsu' if is_matsu else '15'
        # Special: 齋藤 first month (May) = 0.61人月
        actual_req = req
        actual_oka = oka
        if name == '齋藤' and wm == ym(2026,5):
            actual_req = 9150
            actual_oka = 5494  # 9000*0.61≈5494
        results[pm][bucket]['terra'] += actual_req
        results[pm][bucket]['oka_terra'] += actual_oka

# FT
for name,req,is_matsu,s,e,oka,ki in ft_eng:
    for wm in work_months:
        if not active(s,e,wm):
            continue
        pm = next2(wm)
        if pm not in results:
            continue
        bucket = 'matsu' if is_matsu else '15'
        results[pm][bucket]['ft'] += req
        results[pm][bucket]['oka_ft'] += oka
        results[pm][bucket]['kihara_ft'] += ki

# GL
for wm in work_months:
    pm = next2(wm)
    if pm in results:
        results[pm]['15']['gl'] = GL_TOTAL
        results[pm]['15']['kihara_gl'] = GL_KIHARA

# 鶴見 (翌月末日 = work M → pay M+1 末日)
for wm in work_months:
    if wm >= ym(2026,6):
        pm = next1(wm)
        if pm in results:
            results[pm]['matsu']['choku'] = TSURUMI
            results[pm]['matsu']['oka_choku'] = TSURUMI_OKA

# ================================================================
# WRITE TO SHEET
# ================================================================
# Row mapping: 15日/末日/小計 for each payment month
row_map = {}
r = 5
for pm in pay_months:
    row_map[pm] = {'15': r, 'matsu': r+1, 'sub': r+2}
    r += 5  # 15日, 末日, 小計, blank, section_header

# After column insert: cols are now:
# C(3)=TERRA請求, D(4)=源泉, E(5)=TERRA税込, F(6)=TERRA実入り
# G(7)=GL税込, H(8)=FT税込, I(9)=直契約税込, J(10)=岡本払出, K(11)=木原, L(12)=総実入り

batch = []

for pm in pay_months:
    for bucket in ['15','matsu']:
        row = row_map[pm][bucket]
        d = results[pm][bucket]
        
        tr = d['terra']
        gl_v = d['gl']
        ft_v = d['ft']
        choku = d['choku']
        oka = -(d['oka_terra'] + d['oka_ft'] + d['oka_choku'])
        ki = -(d['kihara_ft'] + d['kihara_gl'])
        
        gen = math.floor(tr * 0.1021) if tr > 0 else 0
        tzei = int(tr * 1.1) if tr > 0 else 0
        tri = tzei - gen if tr > 0 else 0
        
        sou = tri + gl_v + ft_v + choku + oka + ki
        
        # For display
        gl_str = gl_v if gl_v > 0 else '-'
        ft_str = ft_v if ft_v > 0 else '-'
        choku_str = choku if choku > 0 else '-'
        oka_str = oka if oka != 0 else '-'
        ki_str = ki if ki != 0 else '-'
        
        batch.append(gspread.Cell(row, 3, tr if tr > 0 else '-'))      # TERRA請求
        batch.append(gspread.Cell(row, 4, gen if gen > 0 else '-'))     # 源泉
        batch.append(gspread.Cell(row, 5, tzei if tzei > 0 else '-'))   # TERRA税込
        batch.append(gspread.Cell(row, 6, tri if tri > 0 else '-'))     # TERRA実入り
        batch.append(gspread.Cell(row, 7, gl_str))                      # GL
        batch.append(gspread.Cell(row, 8, ft_str))                      # FT
        batch.append(gspread.Cell(row, 9, choku_str))                   # 直契約
        batch.append(gspread.Cell(row, 10, oka_str))                    # 岡本
        batch.append(gspread.Cell(row, 11, ki_str))                     # 木原
        batch.append(gspread.Cell(row, 12, sou))                        # 総実入り
    
    # Subtotal row
    sub_row = row_map[pm]['sub']
    d15 = results[pm]['15']
    dma = results[pm]['matsu']
    
    s_tr = d15['terra'] + dma['terra']
    s_gen = math.floor(d15['terra']*0.1021) + math.floor(dma['terra']*0.1021)
    s_tzei = int(d15['terra']*1.1) + int(dma['terra']*1.1)
    s_tri = s_tzei - s_gen
    s_gl = d15['gl'] + dma['gl']
    s_ft = d15['ft'] + dma['ft']
    s_choku = d15['choku'] + dma['choku']
    s_oka = -(d15['oka_terra']+d15['oka_ft']+d15['oka_choku'] +
              dma['oka_terra']+dma['oka_ft']+dma['oka_choku'])
    s_ki = -(d15['kihara_ft']+d15['kihara_gl'] + dma['kihara_ft']+dma['kihara_gl'])
    s_sou = s_tri + s_gl + s_ft + s_choku + s_oka + s_ki
    
    batch.append(gspread.Cell(sub_row, 3, s_tr))
    batch.append(gspread.Cell(sub_row, 4, s_gen))
    batch.append(gspread.Cell(sub_row, 5, s_tzei))
    batch.append(gspread.Cell(sub_row, 6, s_tri))
    batch.append(gspread.Cell(sub_row, 7, s_gl))
    batch.append(gspread.Cell(sub_row, 8, s_ft))
    batch.append(gspread.Cell(sub_row, 9, s_choku if s_choku > 0 else '-'))
    batch.append(gspread.Cell(sub_row, 10, s_oka))
    batch.append(gspread.Cell(sub_row, 11, s_ki))
    batch.append(gspread.Cell(sub_row, 12, s_sou))

# Annual total (Row 64)
ann = [0]*10
for pm in pay_months:
    sub = row_map[pm]['sub']
    # Find this month's subtotal from batch
    for c in batch:
        if c.row == sub:
            col_idx = c.col - 3  # 0-based index into annual array
            if col_idx >= 0 and col_idx < 10:
                v = c.value
                if isinstance(v, str) and v == '-':
                    v = 0
                ann[col_idx] += int(v)

for i in range(10):
    batch.append(gspread.Cell(64, 3+i, ann[i]))

# Write
print(f"Writing {len(batch)} cells...")
yosoku.update_cells(batch, value_input_option='RAW')

# Print summary
print("\n=== UPDATED FORECAST SUMMARY ===")
print(f"{'Month':8} {'TR_req':>8} {'GL':>7} {'FT':>7} {'Choku':>7} {'Oka':>8} {'Ki':>8} {'Sou':>9}")
for pm in pay_months:
    sub = row_map[pm]['sub']
    vals = {}
    for c in batch:
        if c.row == sub:
            vals[c.col] = c.value
    y,m = pm//100, pm%100
    tr = vals.get(3,0)
    gl = vals.get(7,0)
    ft = vals.get(8,0)
    ch = vals.get(9,0); ch = 0 if ch=='-' else ch
    ok = vals.get(10,0)
    ki = vals.get(11,0)
    so = vals.get(12,0)
    print(f"{y}/{m:02d}  {tr:>8,} {gl:>7,} {ft:>7,} {ch:>7,} {ok:>8,} {ki:>8,} {so:>9,}")

print(f"\nAnnual: TR={ann[0]:,} GL={ann[4]:,} FT={ann[5]:,} Ch={ann[6]:,} Oka={ann[7]:,} Ki={ann[8]:,} Sou={ann[9]:,}")
print("=== DONE ===")
