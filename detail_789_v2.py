import math, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def ym(y,m): return y*100+m
def active(s,e,wm): return wm >= s and (e is None or wm <= e)

terra_eng = [
    ('仲山',15000,False,ym(2023,12),None,0),('吉田創志',15000,True,ym(2024,3),None,0),
    ('蒲池',15000,False,ym(2024,3),None,0),('大野',15000,True,ym(2024,4),None,0),
    ('白須',15000,False,ym(2024,5),None,0),('沼田',15000,True,ym(2024,6),None,0),
    ('魚谷',15000,True,ym(2025,4),ym(2026,4),0),('片山',15000,False,ym(2025,4),ym(2026,8),0),
    ('赤木',15000,False,ym(2025,7),None,0),('坪井',15000,True,ym(2025,7),None,0),
    ('中村',15000,True,ym(2025,8),None,0),('日比野',15000,False,ym(2025,9),None,0),
    ('永野',15000,False,ym(2025,10),ym(2026,7),0),('安江',15000,False,ym(2025,10),ym(2026,7),0),
    ('相川',15000,False,ym(2025,10),None,0),('富永',15000,False,ym(2026,1),None,0),
    ('天野',15000,True,ym(2026,1),None,9000),('岩瀬',15000,True,ym(2026,3),None,9000),
    ('橋詰',15000,False,ym(2026,4),None,0),('齋藤',15000,False,ym(2026,5),None,9000),
    ('稲葉',15000,True,ym(2026,7),ym(2026,9),0),
    ('大本BP',15000,False,ym(2025,9),ym(2026,5),0),('森BP',30000,False,ym(2025,9),ym(2026,5),0),
    ('芹澤BP',45000,False,ym(2025,12),None,0),('小山内BP',30000,False,ym(2026,4),None,0),
    ('佐々木BP',40000,False,ym(2026,4),ym(2026,7),20000),
    ('吉田祥平T',40000,False,ym(2026,6),None,0),('佐藤礼奈',25000,False,ym(2026,7),None,0),
]
ft_eng = [
    ('笠井',68000,False,ym(2026,2),None,0,10000),('原FT',68000,False,ym(2026,3),ym(2026,5),0,20000),
    ('木村FT',47600,False,ym(2026,3),None,0,10000),('加藤小坂',38400,False,ym(2026,3),None,0,11000),
    ('川崎FT',27200,False,ym(2026,4),None,0,5000),('田中みさFT',20400,True,ym(2026,4),None,0,0),
    ('立野FT',47600,False,ym(2026,4),None,0,10000),('佐々木FT',27200,False,ym(2026,4),None,0,20000),
    ('橋本FT',47600,False,ym(2026,4),None,17000,10000),('鶴川FT',47600,False,ym(2026,5),None,47600,0),
    ('吉田祥平FT',24000,False,ym(2026,6),None,0,0),('遠藤FT',34000,False,ym(2026,7),None,17000,0),
]
GL=108000; GL_KI=20000; TSURUMI=107800; TSURUMI_OKA=50000

for pay_m, work_m, label in [(7,5,'7月入金(5月稼働分)'), (8,6,'8月入金(6月稼働分)'), (9,7,'9月入金(7月稼働分)')]:
    wm = ym(2026, work_m)
    print(f"\n{'='*80}")
    print(f"■ {label}")
    print(f"{'='*80}")
    
    # --- TERRA ---
    tr15, trm = [], []
    for n,r,im,s,e,o in terra_eng:
        if not active(s,e,wm): continue
        ar,ao = r,o
        if n=='齋藤' and wm==ym(2026,5): ar=9150; ao=5494
        tag = ' ★入場' if wm==s else (' ▼最終月' if e and wm==e else '')
        entry = {'name':n,'req':ar,'oka':ao,'tag':tag}
        (trm if im else tr15).append(entry)
    
    tr15_r = sum(e['req'] for e in tr15); tr15_o = sum(e['oka'] for e in tr15)
    trm_r = sum(e['req'] for e in trm); trm_o = sum(e['oka'] for e in trm)
    g15=math.floor(tr15_r*0.1021); t15=int(tr15_r*1.1); ri15=t15-g15
    gm=math.floor(trm_r*0.1021); tm=int(trm_r*1.1); rim=tm-gm
    tr_ri = ri15+rim
    
    print(f"\n  ■ TERRA 15日  請求(税抜)={tr15_r:,} → 税込={t15:,} → 源泉={g15:,} → 実入り={ri15:,}")
    for e in tr15: print(f"    {e['name']:<10} {e['req']:>6,}(税抜) 岡本={e['oka']:>5,}{e['tag']}")
    print(f"  ■ TERRA 末日  請求(税抜)={trm_r:,} → 税込={tm:,} → 源泉={gm:,} → 実入り={rim:,}")
    for e in trm: print(f"    {e['name']:<10} {e['req']:>6,}(税抜) 岡本={e['oka']:>5,}{e['tag']}")
    
    # --- FT ---
    f15, fm = [], []
    for n,r,im,s,e,o,k in ft_eng:
        if not active(s,e,wm): continue
        tag = ' ★入場' if wm==s else (' ▼最終月' if e and wm==e else '')
        entry = {'name':n,'req':r,'oka':o,'ki':k,'tag':tag}
        (fm if im else f15).append(entry)
    
    f15_r=sum(e['req'] for e in f15); f15_o=sum(e['oka'] for e in f15); f15_k=sum(e['ki'] for e in f15)
    fm_r=sum(e['req'] for e in fm); fm_o=sum(e['oka'] for e in fm); fm_k=sum(e['ki'] for e in fm)
    ft_r = f15_r+fm_r; ft_incl = int(ft_r*1.1)
    
    print(f"\n  ■ FT 15日  税抜={f15_r:,} → 税込={int(f15_r*1.1):,}")
    for e in f15: print(f"    {e['name']:<12} {e['req']:>6,}(税抜) 岡本={e['oka']:>5,} 木原={e['ki']:>5,}{e['tag']}")
    print(f"  ■ FT 末日  税抜={fm_r:,} → 税込={int(fm_r*1.1):,}")
    for e in fm: print(f"    {e['name']:<12} {e['req']:>6,}(税抜) 岡本={e['oka']:>5,} 木原={e['ki']:>5,}{e['tag']}")
    
    # --- GL ---
    gl_incl = int(GL*1.1)
    
    # --- 鶴見: 翌月末日払い → 入金月≧7月ならあり
    has_tsurumi = pay_m >= 7
    choku = TSURUMI if has_tsurumi else 0
    choku_oka = TSURUMI_OKA if has_tsurumi else 0
    
    # --- 集計 ---
    oka_all = tr15_o + trm_o + f15_o + fm_o + choku_oka
    ki_all = f15_k + fm_k + GL_KI
    sou = tr_ri + gl_incl + ft_incl + choku - oka_all - ki_all
    
    print(f"\n  {'━'*70}")
    print(f"  ■ 月次集計")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"    TERRA実入り(税込-源泉)        {tr_ri:>10,}")
    print(f"    GL   {GL:>7,}(税抜) × 1.1 =    {gl_incl:>10,}  (税込)")
    print(f"    FT   {ft_r:>7,}(税抜) × 1.1 =    {ft_incl:>10,}  (税込)")
    if has_tsurumi:
        print(f"    直契約(税込/2%割引後)         {choku:>10,}")
    else:
        print(f"    直契約                                  -")
    print(f"    ─────────────────────────────────────────")
    print(f"    収入合計                      {tr_ri+gl_incl+ft_incl+choku:>10,}")
    print(f"")
    print(f"    岡本(税抜)  TERRA={tr15_o+trm_o:,} FT={f15_o+fm_o:,}" + (f" 鶴見={choku_oka:,}" if has_tsurumi else ""))
    print(f"                                 △{oka_all:>10,}")
    print(f"    木原(税抜)  FT={f15_k+fm_k:,} GL={GL_KI:,}")
    print(f"                                 △{ki_all:>10,}")
    print(f"    ─────────────────────────────────────────")
    print(f"    ■ 総実入り                    {sou:>10,}")
    print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

print(f"\n{'='*80}")
print(f"■ 3ヵ月推移")
print(f"{'='*80}")
print(f"  7月:  874,295  鶴見初回入金・鶴川FT参入")
print(f"  8月:  843,237  吉田祥平(TR40k+FT24k)参入、原FT退場")
print(f"  9月:  903,552  佐藤礼奈+稲葉+遠藤の3名参入 ★ピーク")
print(f"")
print(f"  6月→9月: +80,486（+9.8%）")
