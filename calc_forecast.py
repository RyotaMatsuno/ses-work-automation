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

# ================================================================
# ENGINEER DATA (from contract sheets)
# ================================================================
# Payment timing: site30 → (M+1)末日, site35-45 → (M+2)15日, site50-60 → (M+2)末日
# Month encoding: 202604=April 2026, etc.

def ym(y, m):
    return y * 100 + m

# --- TERRA engineers ---
# (name, tr_req, site, start_ym, end_ym, oka_per_month)
# end_ym=None means ongoing
terra = [
    # Standard P (ongoing)
    ('仲山', 15000, 45, ym(2023,12), None, 0),
    ('吉田創志', 15000, 50, ym(2024,3), None, 0),
    ('蒲池', 15000, 45, ym(2024,3), None, 0),
    ('大野', 15000, 55, ym(2024,4), None, 0),
    ('白須', 15000, 45, ym(2024,5), None, 0),
    ('沼田', 15000, 55, ym(2024,6), None, 0),
    ('魚谷', 15000, 55, ym(2025,4), ym(2026,4), 0),     # 4月終了
    ('片山', 15000, 30, ym(2025,4), ym(2026,7), 0),      # 7月末終了
    ('赤木', 15000, 40, ym(2025,7), None, 0),
    ('坪井', 15000, 50, ym(2025,7), None, 0),
    ('中村', 15000, 50, ym(2025,8), None, 0),
    ('日比野', 15000, 40, ym(2025,9), None, 0),
    ('永野', 15000, 45, ym(2025,10), None, 0),
    ('安江', 15000, 45, ym(2025,10), None, 0),
    ('相川', 15000, 40, ym(2025,10), None, 0),
    ('富永', 15000, 40, ym(2026,1), None, 0),
    ('天野', 15000, 50, ym(2026,1), None, 9000),         # 岡本
    ('岩瀬', 15000, 50, ym(2026,3), None, 9000),         # 岡本
    ('加藤T', 15000, 45, ym(2026,3), ym(2026,4), 9000),  # 岡本, 退場 ~April
    ('齋藤', 15000, 45, ym(2026,5), None, 9000),         # 岡本, 初月5/15→0.61人月
    ('稲葉', 15000, 60, ym(2026,7), ym(2026,9), 0),      # 9月末終了
    # BPs
    ('大本BP', 15000, 35, ym(2025,9), ym(2026,5), 0),    # TERRA折半 30k粗利×50%=15k, 5月末終了
    ('森BP', 30000, 40, ym(2025,9), ym(2026,5), 0),      # TERRA折半 60k×50%=30k, 5月末終了
    ('芹澤BP', 45000, 40, ym(2025,12), None, 0),         # TERRA折半 90k×50%=45k
    ('小山内BP', 30000, 45, ym(2026,4), None, 0),         # TERRA折半 60k×50%=30k
    ('佐々木BP', 40000, 45, ym(2026,4), None, 20000),     # 岡本折半
    ('吉田祥平T', 40000, 45, ym(2026,6), None, 0),       # BP, TERRA側松野のみ
    # 請求なし entries are excluded (山内清,田中みさ,木村,原,川崎新,橋詰)
]

# --- FT engineers ---
# (name, ft_req, site, start_ym, end_ym, oka, kihara)
ft = [
    ('笠井', 68000, 45, ym(2026,2), None, 0, 10000),
    ('原FT', 68000, 45, ym(2026,3), ym(2026,5), 0, 20000),    # 5月末終了
    ('木村FT', 47600, 45, ym(2026,3), None, 0, 10000),
    ('加藤小坂', 38400, 45, ym(2026,3), None, 0, 11000),       # 小坂折半
    ('川崎FT', 27200, 45, ym(2026,4), None, 0, 5000),
    ('田中みさFT', 20400, 55, ym(2026,4), None, 0, 0),
    ('立野FT', 47600, 45, ym(2026,4), None, 0, 10000),
    ('佐々木FT', 27200, 45, ym(2026,4), None, 0, 20000),
    ('橋本FT', 47600, 45, ym(2026,4), None, 0, 10000),         # 岡本折半→oka is in TERRA side
    ('鶴川FT', 47600, 45, ym(2026,5), None, 47600, 0),         # 岡本全額払出
    ('吉田祥平FT', 24000, 45, ym(2026,6), None, 0, 0),        # 小坂折半
    ('遠藤FT', 34000, 45, ym(2026,7), None, 17000, 0),         # 岡本折半
]

# --- GL engineers (all site ~45, paid 15日) ---
# (name, gl_req, start_ym, end_ym, kihara)
gl = [
    ('石崎GL', 24000, ym(2024,9), None, 0),    # 40k粗利×60%
    ('山内GL', 42000, ym(2024,10), None, 10000),
    ('荒井GL', 42000, ym(2025,6), None, 10000),
]
# GL total = 108000 (verified)

# ================================================================
# FORECAST CALCULATION
# ================================================================
# Work months: April 2026 (202604) through March 2027 (202703)
# Payment months: June 2026 through May 2027

work_months = [ym(2026, m) for m in range(4, 13)] + [ym(2027, m) for m in range(1, 4)]
# [202604, 202605, ..., 202612, 202701, 202702, 202703]

def is_active(eng_start, eng_end, work_ym):
    if work_ym < eng_start:
        return False
    if eng_end is not None and work_ym > eng_end:
        return False
    return True

def get_payment_bucket(site, work_ym):
    """Returns (payment_month_ym, '15' or 'matsu')"""
    y = work_ym // 100
    m = work_ym % 100
    
    if site <= 30:
        # (M+1) 末日
        nm = m + 1
        ny = y + (nm - 1) // 12
        nm = ((nm - 1) % 12) + 1
        return (ym(ny, nm), 'matsu')
    elif site <= 45:
        # (M+2) 15日
        nm = m + 2
        ny = y + (nm - 1) // 12
        nm = ((nm - 1) % 12) + 1
        return (ym(ny, nm), '15')
    else:  # 50-60
        # (M+2) 末日
        nm = m + 2
        ny = y + (nm - 1) // 12
        nm = ((nm - 1) % 12) + 1
        return (ym(ny, nm), 'matsu')

# Initialize forecast structure
# payment_months: June 2026 to May 2027
pay_months = [ym(2026, m) for m in range(6, 13)] + [ym(2027, m) for m in range(1, 6)]

forecast = {}
for pm in pay_months:
    forecast[pm] = {
        '15': {'terra': 0, 'gl': 0, 'ft': 0, 'oka_terra': 0, 'oka_ft': 0, 'kihara': 0},
        'matsu': {'terra': 0, 'gl': 0, 'ft': 0, 'oka_terra': 0, 'oka_ft': 0, 'kihara': 0},
    }

# Process TERRA
for name, tr_req, site, start, end, oka in terra:
    for wm in work_months:
        if not is_active(start, end, wm):
            continue
        pay_ym, bucket = get_payment_bucket(site, wm)
        if pay_ym in forecast:
            forecast[pay_ym][bucket]['terra'] += tr_req
            forecast[pay_ym][bucket]['oka_terra'] += oka

# Special: 齋藤 初月(May) 0.61人月 → TR_req=15000×0.61=9150
# Correction: May work for 齋藤 should be 9150, not 15000
# 齋藤 is already added as 15000 for all months including May
# Need to subtract the difference for May
saito_may_pay_ym, saito_may_bucket = get_payment_bucket(45, ym(2026, 5))
forecast[saito_may_pay_ym][saito_may_bucket]['terra'] -= (15000 - 9150)
forecast[saito_may_pay_ym][saito_may_bucket]['oka_terra'] -= (9000 - 5494)  # 9000×0.61≈5494

# Process FT
for name, ft_req, site, start, end, oka, kihara in ft:
    for wm in work_months:
        if not is_active(start, end, wm):
            continue
        pay_ym, bucket = get_payment_bucket(site, wm)
        if pay_ym in forecast:
            forecast[pay_ym][bucket]['ft'] += ft_req
            forecast[pay_ym][bucket]['oka_ft'] += oka
            forecast[pay_ym][bucket]['kihara'] += kihara

# Process GL (all assumed site45 → 15日)
for name, gl_req, start, end, kihara in gl:
    for wm in work_months:
        if not is_active(start, end, wm):
            continue
        for pm in pay_months:
            pass  # handled below
        pay_ym, bucket = get_payment_bucket(45, wm)
        if pay_ym in forecast:
            forecast[pay_ym][bucket]['gl'] += gl_req
            forecast[pay_ym][bucket]['kihara'] += kihara

# 鶴見直契約: 10万税抜×0.98(2%割引)×1.1=107,800税込, 翌月末日, 6月稼働~
# 岡本50,000/月
TSURUMI = 107800
TSURUMI_OKA = -50000
for wm in work_months:
    if wm >= ym(2026, 6):
        # 翌月末日 → サイト30相当
        pay_ym, bucket = get_payment_bucket(30, wm)
        if pay_ym in forecast:
            forecast[pay_ym][bucket]['choku'] = forecast[pay_ym][bucket].get('choku', 0) + TSURUMI
            forecast[pay_ym][bucket]['oka_choku'] = forecast[pay_ym][bucket].get('oka_choku', 0) + TSURUMI_OKA

# ================================================================
# BUILD OUTPUT
# ================================================================
print("=== FORECAST RESULTS ===")
print(f"{'Payment':12} {'Bucket':6} {'TERRA':>8} {'GL':>8} {'FT':>8} {'Choku':>8} {'Oka':>8} {'Kihara':>8} {'Total':>8}")

annual = {'terra':0, 'gensen':0, 'terra_zei':0, 'terra_ri':0, 'gl':0, 'ft':0, 'choku':0, 'oka':0, 'kihara':0, 'sou':0}

for pm in pay_months:
    y = pm // 100
    m = pm % 100
    
    for bucket in ['15', 'matsu']:
        d = forecast[pm][bucket]
        tr = d['terra']
        gl_v = d['gl']
        ft_v = d['ft']
        choku = d.get('choku', 0)
        oka = -(d['oka_terra'] + d['oka_ft'] + abs(d.get('oka_choku', 0)))
        kihara = -d['kihara']
        
        # TERRA calculations
        gensen = math.floor(tr * 0.1021) if tr > 0 else 0
        terra_zei = int(tr * 1.1) if tr > 0 else 0
        terra_ri = terra_zei - gensen if tr > 0 else 0
        
        total = terra_ri + gl_v + ft_v + choku + oka + kihara
        
        print(f"{y}/{m:02d}/{('15' if bucket=='15' else '末'):>3} {bucket:6} "
              f"TR={tr:>7} GL={gl_v:>7} FT={ft_v:>7} Ch={choku:>7} "
              f"Oka={oka:>7} Ki={kihara:>7} "
              f"TRri={terra_ri:>7} Sou={total:>8}")
    
    # Subtotals
    d15 = forecast[pm]['15']
    dma = forecast[pm]['matsu']
    tr_total = d15['terra'] + dma['terra']
    gl_total = d15['gl'] + dma['gl']
    ft_total = d15['ft'] + dma['ft']
    choku_total = d15.get('choku',0) + dma.get('choku',0)
    oka_total = -(d15['oka_terra']+d15['oka_ft']+abs(d15.get('oka_choku',0)) + 
                  dma['oka_terra']+dma['oka_ft']+abs(dma.get('oka_choku',0)))
    ki_total = -(d15['kihara'] + dma['kihara'])
    
    gen_total = math.floor(d15['terra']*0.1021) + math.floor(dma['terra']*0.1021)
    tzei_total = int(d15['terra']*1.1) + int(dma['terra']*1.1)
    tri_total = tzei_total - gen_total
    sou_total = tri_total + gl_total + ft_total + choku_total + oka_total + ki_total
    
    print(f"  SUBTOTAL: TR_req={tr_total:>7} Gen={gen_total:>6} TZei={tzei_total:>7} TRi={tri_total:>7} "
          f"GL={gl_total:>7} FT={ft_total:>7} Ch={choku_total:>7} Oka={oka_total:>7} Ki={ki_total:>7} Sou={sou_total:>8}")
    
    annual['terra'] += tr_total
    annual['gensen'] += gen_total
    annual['terra_zei'] += tzei_total
    annual['terra_ri'] += tri_total
    annual['gl'] += gl_total
    annual['ft'] += ft_total
    annual['choku'] += choku_total
    annual['oka'] += oka_total
    annual['kihara'] += ki_total
    annual['sou'] += sou_total
    print()

print(f"\n=== ANNUAL TOTAL ===")
for k, v in annual.items():
    print(f"  {k}: {v:,}")
