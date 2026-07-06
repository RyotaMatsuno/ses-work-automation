import gspread, math, sys, io
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

def ym(y,m): return y*100+m
def active(s,e,wm): return wm >= s and (e is None or wm <= e)
def next2(wm):
    y,m = wm//100, wm%100; m+=2
    if m>12: y+=1; m-=12
    return ym(y,m)
def next1(wm):
    y,m = wm//100, wm%100; m+=1
    if m>12: y+=1; m-=12
    return ym(y,m)

# ================================================================
# ENGINEER DATA - 加藤T修正: end=2026/3(3月最終→5月入金=予測外)
# ================================================================
terra_eng = [
    # (name, req, is_matsu, start, end, oka)
    ('仲山',15000,False, ym(2023,12),None, 0),
    ('吉田創志',15000,True, ym(2024,3),None, 0),
    ('蒲池',15000,False, ym(2024,3),None, 0),
    ('大野',15000,True, ym(2024,4),None, 0),
    ('白須',15000,False, ym(2024,5),None, 0),
    ('沼田',15000,True, ym(2024,6),None, 0),
    ('魚谷',15000,True, ym(2025,4),ym(2026,4), 0),      # 4月終了→6月末最終入金
    ('片山',15000,False, ym(2025,4),ym(2026,7), 0),      # 7月末終了→9月15日最終入金
    ('赤木',15000,False, ym(2025,7),None, 0),
    ('坪井',15000,True, ym(2025,7),None, 0),
    ('中村',15000,True, ym(2025,8),None, 0),
    ('日比野',15000,False, ym(2025,9),None, 0),
    ('永野',15000,False, ym(2025,10),None, 0),
    ('安江',15000,False, ym(2025,10),None, 0),
    ('相川',15000,False, ym(2025,10),None, 0),
    ('富永',15000,False, ym(2026,1),None, 0),
    ('天野',15000,True, ym(2026,1),None, 9000),          # 岡本①
    ('岩瀬',15000,True, ym(2026,3),None, 9000),          # 岡本②
    # ★加藤T: 退場済み→予測期間に影響なし(3月最終稼働→5月入金)
    ('橋詰',15000,False, ym(2026,4),None, 0),
    ('齋藤',15000,False, ym(2026,5),None, 9000),         # 岡本③ 5月入場
    ('稲葉',15000,True, ym(2026,7),ym(2026,9), 0),      # 9月末終了
    # BPs
    ('大本BP',15000,False, ym(2025,9),ym(2026,5), 0),    # 5月末終了→7月15日最終
    ('森BP',30000,False, ym(2025,9),ym(2026,5), 0),      # 5月末終了→7月15日最終
    ('芹澤BP',45000,False, ym(2025,12),None, 0),
    ('小山内BP',30000,False, ym(2026,4),None, 0),
    ('佐々木BP',40000,False, ym(2026,4),None, 20000),    # 岡本折半
    ('吉田祥平T',40000,False, ym(2026,6),None, 0),      # ★6月入場→8月15日初回
]

ft_eng = [
    # (name, req, is_matsu, start, end, oka, kihara)
    ('笠井',68000,False, ym(2026,2),None, 0, 10000),
    ('原FT',68000,False, ym(2026,3),ym(2026,5), 0, 20000),  # 5月末終了→7月15日最終
    ('木村FT',47600,False, ym(2026,3),None, 0, 10000),
    ('加藤小坂',38400,False, ym(2026,3),None, 0, 11000),
    ('川崎FT',27200,False, ym(2026,4),None, 0, 5000),
    ('田中みさFT',20400,True, ym(2026,4),None, 0, 0),
    ('立野FT',47600,False, ym(2026,4),None, 0, 10000),
    ('佐々木FT',27200,False, ym(2026,4),None, 0, 20000),
    ('橋本FT',47600,False, ym(2026,4),None, 23800, 10000),  # 岡本折半
    ('鶴川FT',47600,False, ym(2026,5),None, 47600, 0),      # 岡本全額払出
    ('吉田祥平FT',24000,False, ym(2026,6),None, 0, 0),     # ★6月入場→8月15日初回
    ('遠藤FT',34000,False, ym(2026,7),None, 17000, 0),      # ★7月入場→9月15日初回
]

GL_TOTAL = 108000
GL_KIHARA = 20000
TSURUMI = int(100000 * 0.98 * 1.1)  # 107800
TSURUMI_OKA = 50000

# ================================================================
# PRINT ENTRY/EXIT TIMELINE
# ================================================================
print("=== 入退場タイムライン ===")
print(f"{'名前':<14} {'区分':>5} {'稼働開始':>8} {'稼働終了':>10} {'初回入金':>10} {'最終入金':>10} {'岡本':>6}")
all_people = []
for n,r,im,s,e,o in terra_eng:
    pm_start = next2(s)
    pm_end = next2(e) if e else 'ongoing'
    bucket_s = '末' if im else '15'
    all_people.append((n, 'TERRA', s, e, pm_start, pm_end, o, r))
for n,r,im,s,e,o,k in ft_eng:
    pm_start = next2(s)
    pm_end = next2(e) if e else 'ongoing'
    all_people.append((n, 'FT', s, e, pm_start, pm_end, o, r))

for n, cat, s, e, ps, pe, o, r in sorted(all_people, key=lambda x: x[2]):
    sy,sm = s//100,s%100
    es = f"{e//100}/{e%100:02d}" if e else '継続中'
    pss = f"{ps//100}/{ps%100:02d}" if isinstance(ps,int) else ps
    pes = f"{pe//100}/{pe%100:02d}" if isinstance(pe,int) else pe
    print(f"  {n:<12} {cat:>5} {sy}/{sm:02d}     {es:>10} {pss:>10} {pes:>10} {o:>6} ({r:,})")

# ================================================================
# CALCULATE FORECAST
# ================================================================
work_months = [ym(2026,m) for m in range(4,13)] + [ym(2027,m) for m in range(1,4)]
pay_months = [ym(2026,m) for m in range(6,13)] + [ym(2027,m) for m in range(1,6)]

results = {}
for pm in pay_months:
    results[pm] = {b: {'terra':0,'ft':0,'gl':0,'choku':0,
                       'oka_t':0,'oka_f':0,'oka_c':0,'ki_f':0,'ki_g':0}
                   for b in ['15','matsu']}

for name,req,is_matsu,s,e,oka in terra_eng:
    for wm in work_months:
        if not active(s,e,wm): continue
        pm = next2(wm)
        if pm not in results: continue
        b = 'matsu' if is_matsu else '15'
        actual_req = req
        actual_oka = oka
        if name == '齋藤' and wm == ym(2026,5):
            actual_req = 9150; actual_oka = 5494
        results[pm][b]['terra'] += actual_req
        results[pm][b]['oka_t'] += actual_oka

for name,req,is_matsu,s,e,oka,ki in ft_eng:
    for wm in work_months:
        if not active(s,e,wm): continue
        pm = next2(wm)
        if pm not in results: continue
        b = 'matsu' if is_matsu else '15'
        results[pm][b]['ft'] += req
        results[pm][b]['oka_f'] += oka
        results[pm][b]['ki_f'] += ki

for wm in work_months:
    pm = next2(wm)
    if pm in results:
        results[pm]['15']['gl'] = GL_TOTAL
        results[pm]['15']['ki_g'] = GL_KIHARA

for wm in work_months:
    if wm >= ym(2026,6):
        pm = next1(wm)
        if pm in results:
            results[pm]['matsu']['choku'] = TSURUMI
            results[pm]['matsu']['oka_c'] = TSURUMI_OKA

# ================================================================
# WRITE TO SHEET
# ================================================================
row_map = {}
r = 5
for pm in pay_months:
    row_map[pm] = {'15': r, 'matsu': r+1, 'sub': r+2}
    r += 5

batch = []
for pm in pay_months:
    for bucket in ['15','matsu']:
        row = row_map[pm][bucket]
        d = results[pm][bucket]
        tr = d['terra']; gl_v = d['gl']; ft_v = d['ft']; ch = d['choku']
        oka = -(d['oka_t'] + d['oka_f'] + d['oka_c'])
        ki = -(d['ki_f'] + d['ki_g'])
        gen = math.floor(tr*0.1021) if tr>0 else 0
        tzei = int(tr*1.1) if tr>0 else 0
        tri = tzei-gen if tr>0 else 0
        sou = tri + gl_v + ft_v + ch + oka + ki
        for col,val in [(3,tr),(4,gen),(5,tzei),(6,tri),(7,gl_v),(8,ft_v),(9,ch),(10,oka),(11,ki),(12,sou)]:
            batch.append(gspread.Cell(row, col, val if val!=0 else '-'))

    sub_row = row_map[pm]['sub']
    d15 = results[pm]['15']; dma = results[pm]['matsu']
    s_tr = d15['terra']+dma['terra']
    s_gen = math.floor(d15['terra']*0.1021)+math.floor(dma['terra']*0.1021)
    s_tzei = int(d15['terra']*1.1)+int(dma['terra']*1.1)
    s_tri = s_tzei - s_gen
    s_gl = d15['gl']+dma['gl']; s_ft = d15['ft']+dma['ft']; s_ch = d15['choku']+dma['choku']
    s_oka = -(d15['oka_t']+d15['oka_f']+d15['oka_c']+dma['oka_t']+dma['oka_f']+dma['oka_c'])
    s_ki = -(d15['ki_f']+d15['ki_g']+dma['ki_f']+dma['ki_g'])
    s_sou = s_tri + s_gl + s_ft + s_ch + s_oka + s_ki
    for col,val in [(3,s_tr),(4,s_gen),(5,s_tzei),(6,s_tri),(7,s_gl),(8,s_ft),(9,s_ch if s_ch>0 else '-'),(10,s_oka),(11,s_ki),(12,s_sou)]:
        batch.append(gspread.Cell(sub_row, col, val))

# Annual total
ann = [0]*10
for pm in pay_months:
    sr = row_map[pm]['sub']
    for c in batch:
        if c.row==sr and 3<=c.col<=12:
            v = 0 if c.value=='-' else int(c.value)
            ann[c.col-3] += v
for i in range(10):
    batch.append(gspread.Cell(64, 3+i, ann[i]))

print(f"\nWriting {len(batch)} cells...")
yosoku.update_cells(batch, value_input_option='RAW')

# ================================================================
# PRINT FINAL SUMMARY
# ================================================================
print("\n=== 更新後サマリー（全項目）===")
print(f"{'月':>4} | {'TR実入':>8} | {'GL':>7} | {'FT':>7} | {'直契約':>7} | {'岡本':>8} | {'木原':>8} | {'総実入':>9}")
print("-"*80)
ann_sou = 0
for pm in pay_months:
    sr = row_map[pm]['sub']
    vals = {}
    for c in batch:
        if c.row==sr: vals[c.col] = 0 if c.value=='-' else int(c.value)
    y,m = pm//100, pm%100
    mo = f"{m}月"
    print(f"{mo:>4} | {vals[6]:>8,} | {vals[7]:>7,} | {vals[8]:>7,} | {vals.get(9,0):>7,} | {vals[10]:>8,} | {vals[11]:>8,} | {vals[12]:>9,}")
    ann_sou += vals[12]

print("-"*80)
print(f"年間 | {ann[3]:>8,} | {ann[4]:>7,} | {ann[5]:>7,} | {ann[6]:>7,} | {ann[7]:>8,} | {ann[8]:>8,} | {ann_sou:>9,}")
print(f"\n月平均: {ann_sou//12:,}")

# 岡本内訳
print("\n=== 岡本内訳（9月安定期）===")
print("  TERRA岡本: 天野9k + 岩瀬9k + 齋藤9k + 佐々木BP20k = 47,000")
print("  FT岡本: 橋本23.8k + 鶴川47.6k + 遠藤17k = 88,400")
print("  直契約岡本: 鶴見50k")
print(f"  合計: -{47000+88400+50000:,}")
print("  ※加藤T: 退場済み→予測から除外")
