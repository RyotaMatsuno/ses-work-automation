import math, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def ym(y,m): return y*100+m
def active(s,e,wm): return wm >= s and (e is None or wm <= e)

terra_eng = [
    ('仲山',15000,False,ym(2023,12),None,0),
    ('吉田創志',15000,True,ym(2024,3),None,0),
    ('蒲池',15000,False,ym(2024,3),None,0),
    ('大野',15000,True,ym(2024,4),None,0),
    ('白須',15000,False,ym(2024,5),None,0),
    ('沼田',15000,True,ym(2024,6),None,0),
    ('魚谷',15000,True,ym(2025,4),ym(2026,4),0),
    ('片山',15000,False,ym(2025,4),ym(2026,8),0),
    ('赤木',15000,False,ym(2025,7),None,0),
    ('坪井',15000,True,ym(2025,7),None,0),
    ('中村',15000,True,ym(2025,8),None,0),
    ('日比野',15000,False,ym(2025,9),None,0),
    ('永野',15000,False,ym(2025,10),ym(2026,7),0),
    ('安江',15000,False,ym(2025,10),ym(2026,7),0),
    ('相川',15000,False,ym(2025,10),None,0),
    ('富永',15000,False,ym(2026,1),None,0),
    ('天野',15000,True,ym(2026,1),None,9000),
    ('岩瀬',15000,True,ym(2026,3),None,9000),
    ('橋詰',15000,False,ym(2026,4),None,0),
    ('齋藤',15000,False,ym(2026,5),None,9000),
    ('稲葉',15000,True,ym(2026,7),ym(2026,9),0),
    ('大本BP',15000,False,ym(2025,9),ym(2026,5),0),
    ('森BP',30000,False,ym(2025,9),ym(2026,5),0),
    ('芹澤BP',45000,False,ym(2025,12),None,0),
    ('小山内BP',30000,False,ym(2026,4),None,0),
    ('佐々木BP',40000,False,ym(2026,4),ym(2026,7),20000),
    ('吉田祥平T',40000,False,ym(2026,6),None,0),
    ('佐藤礼奈',25000,False,ym(2026,7),None,0),
]
ft_eng = [
    ('笠井',68000,False,ym(2026,2),None,0,10000),
    ('原FT',68000,False,ym(2026,3),ym(2026,5),0,20000),
    ('木村FT',47600,False,ym(2026,3),None,0,10000),
    ('加藤小坂',38400,False,ym(2026,3),None,0,11000),
    ('川崎FT',27200,False,ym(2026,4),None,0,5000),
    ('田中みさFT',20400,True,ym(2026,4),None,0,0),
    ('立野FT',47600,False,ym(2026,4),None,0,10000),
    ('佐々木FT',27200,False,ym(2026,4),None,0,20000),
    ('橋本FT',47600,False,ym(2026,4),None,17000,10000),
    ('鶴川FT',47600,False,ym(2026,5),None,47600,0),
    ('吉田祥平FT',24000,False,ym(2026,6),None,0,0),
    ('遠藤FT',34000,False,ym(2026,7),None,17000,0),
]

GL_TOTAL=108000; GL_KIHARA=20000
TSURUMI=107800; TSURUMI_OKA=50000

# 7月=5月稼働, 8月=6月稼働, 9月=7月稼働
for pay_m, work_m, label in [(7,5,'7月入金(5月稼働)'), (8,6,'8月入金(6月稼働)'), (9,7,'9月入金(7月稼働)')]:
    wm = ym(2026, work_m)
    print(f"\n{'='*90}")
    print(f"■ {label}")
    print(f"{'='*90}")
    
    # TERRA
    tr15_names, tr15_total, tr15_oka = [], 0, 0
    trm_names, trm_total, trm_oka = [], 0, 0
    for n,r,im,s,e,o in terra_eng:
        if not active(s,e,wm): continue
        ar,ao = r,o
        if n=='齋藤' and wm==ym(2026,5): ar=9150; ao=5494
        tag = ''
        if wm == s: tag = ' ★NEW'
        elif e and wm == e: tag = ' ▼LAST'
        if im:
            trm_names.append(f"    {n}: {ar:,}(税抜) oka={ao:,}{tag}")
            trm_total += ar; trm_oka += ao
        else:
            tr15_names.append(f"    {n}: {ar:,}(税抜) oka={ao:,}{tag}")
            tr15_total += ar; tr15_oka += ao
    
    print(f"\n  【TERRA 15日】請求合計(税抜): {tr15_total:,}")
    for n in tr15_names: print(n)
    gen15 = math.floor(tr15_total*0.1021)
    tzei15 = int(tr15_total*1.1)
    tri15 = tzei15 - gen15
    print(f"    → 税込={tzei15:,} - 源泉={gen15:,} = 実入り {tri15:,}")
    
    print(f"\n  【TERRA 末日】請求合計(税抜): {trm_total:,}")
    for n in trm_names: print(n)
    genm = math.floor(trm_total*0.1021)
    tzeim = int(trm_total*1.1)
    trim = tzeim - genm
    print(f"    → 税込={tzeim:,} - 源泉={genm:,} = 実入り {trim:,}")
    
    tr_total = tr15_total + trm_total
    tr_ri = tri15 + trim
    print(f"  【TERRA計】請求(税抜)={tr_total:,} → 実入り={tr_ri:,}")
    
    # FT
    ft15_names, ft15_total, ft15_oka, ft15_ki = [], 0, 0, 0
    ftm_names, ftm_total, ftm_oka, ftm_ki = [], 0, 0, 0
    for n,r,im,s,e,o,k in ft_eng:
        if not active(s,e,wm): continue
        tag = ''
        if wm == s: tag = ' ★NEW'
        elif e and wm == e: tag = ' ▼LAST'
        if im:
            ftm_names.append(f"    {n}: {r:,}(税抜) oka={o:,} ki={k:,}{tag}")
            ftm_total += r; ftm_oka += o; ftm_ki += k
        else:
            ft15_names.append(f"    {n}: {r:,}(税抜) oka={o:,} ki={k:,}{tag}")
            ft15_total += r; ft15_oka += o; ft15_ki += k
    
    ft_total = ft15_total + ftm_total
    ft_incl = int(ft_total * 1.1)
    print(f"\n  【FT 15日】合計(税抜): {ft15_total:,} → 税込: {int(ft15_total*1.1):,}")
    for n in ft15_names: print(n)
    print(f"  【FT 末日】合計(税抜): {ftm_total:,} → 税込: {int(ftm_total*1.1):,}")
    for n in ftm_names: print(n)
    print(f"  【FT計】税抜={ft_total:,} → 税込={ft_incl:,}")
    
    # GL
    gl_incl = int(GL_TOTAL * 1.1)
    print(f"\n  【GL】税抜={GL_TOTAL:,} → 税込={gl_incl:,}")
    
    # 直契約
    has_tsurumi = wm >= ym(2026,6)  # June work → July末 payment
    choku = TSURUMI if has_tsurumi else 0
    choku_oka = TSURUMI_OKA if has_tsurumi else 0
    print(f"  【直契約(鶴見)】税込={choku:,} (2%割引後)")
    
    # 岡本
    oka_total = tr15_oka + trm_oka + ft15_oka + ftm_oka + choku_oka
    print(f"\n  【岡本払出(税抜)】")
    print(f"    TERRA: 齋藤{tr15_oka-20000 if tr15_oka>20000 else tr15_oka}含む15日={tr15_oka:,} + 末日(天野+岩瀬)={trm_oka:,}")
    print(f"    FT: 15日={ft15_oka:,} + 末日={ftm_oka:,}")
    if has_tsurumi:
        print(f"    直契約: 鶴見={choku_oka:,}")
    print(f"    合計(税抜): △{oka_total:,}")
    
    # 木原
    ki_total = ft15_ki + ftm_ki + GL_KIHARA
    print(f"  【木原(税抜)】FT={ft15_ki+ftm_ki:,} + GL={GL_KIHARA:,} = △{ki_total:,}")
    
    # 総実入り
    sou = tr_ri + gl_incl + ft_incl + choku - oka_total - ki_total
    print(f"\n  {'─'*60}")
    print(f"  【総実入り】")
    print(f"    TERRA実入り          {tr_ri:>10,}  (税込-源泉)")
    print(f"    GL(税抜)×1.1         {gl_incl:>10,}  (税込)")
    print(f"    FT(税抜)×1.1         {ft_incl:>10,}  (税込)")
    print(f"    直契約(税込)         {choku:>10,}  (税込)")
    print(f"    岡本(税抜)          {-oka_total:>10,}")
    print(f"    木原(税抜)          {-ki_total:>10,}")
    print(f"    ─────────────────────────")
    print(f"    総実入り             {sou:>10,}")

# 比較
print(f"\n{'='*90}")
print(f"■ 月別比較")
print(f"{'='*90}")
print(f"  7月:  874,295  ← 鶴見初回入金+鶴川FT参入")
print(f"  8月:  843,237  ← 吉田祥平(TR+FT)参入、原FT最終")
print(f"  9月:  903,552  ← 佐藤礼奈+稲葉+遠藤参入 ★ピーク")
print(f"  増加: 6月(823k) → 9月(903k) = +80,486 (+9.8%)")
