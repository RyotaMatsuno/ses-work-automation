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

# ============================================================
# 1. TERRAマスターに菊池を追加
# ============================================================
terra = sh.worksheet('TERRA')
t_all = terra.get_all_values()

# Find insert position (before 合計行)
insert_row = len(t_all) + 1
for i in range(len(t_all)-1, 3, -1):
    if '合計' in str(t_all[i][0]):
        insert_row = i + 1  # 1-indexed
        break

terra.insert_row([
    '岡本',                # 担当
    'BP',                  # 区分
    '入場前',              # ステータス
    '菊池',                # 氏名
    '2026/7',              # 参画時期
    '長期',                # 期間
    'アルコール飲料製造販売会社 システム開発',  # 案件
    '800000',              # 単価(案件/上位)
    '45',                  # 支払サイト
    '',                    # 勤怠表フロー(有)
    '単月更新',            # 更新サイクル
    'システム開発',        # 業務内容
    '',                    # 仕入先
    '750000',              # 仕入単価
    '50000',               # 粗利
    '40000',               # TERRA請求(粗利×80%)
    '35000',               # 岡本払出(粗利×70%)
    '5000',                # 実入り(粗利×10%)
    'TERRA岡本担当BP。粗利5万×80%=40,000請求。粗利×70%=35,000岡本払出。松野実入り5,000。精算140-180h。田町。',
    '',                    # 7月稼働確定
    '準委任',              # 契約区分
], index=insert_row)

print(f"[OK] 菊池をTERRA Row{insert_row}に追加")

# ============================================================
# 2. 入金予測を更新（菊池追加）
# ============================================================
yosoku = sh.worksheet('入金予測')

def ym(y,m): return y*100+m
def active(s,e,wm): return wm >= s and (e is None or wm <= e)
def next2(wm):
    y,m=wm//100,wm%100; m+=2
    if m>12: y+=1; m-=12
    return ym(y,m)
def next1(wm):
    y,m=wm//100,wm%100; m+=1
    if m>12: y+=1; m-=12
    return ym(y,m)

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
    ('菊池',40000,False,ym(2026,7),None,35000),  # ★NEW 岡本担当BP 粗利80%請求/70%払出
]
ft_eng = [
    ('笠井',68000,False,ym(2026,2),None,0,10000),('原FT',68000,False,ym(2026,3),ym(2026,5),0,20000),
    ('木村FT',47600,False,ym(2026,3),None,0,10000),('加藤小坂',38400,False,ym(2026,3),None,0,11000),
    ('川崎FT',27200,False,ym(2026,4),None,0,5000),('田中みさFT',20400,True,ym(2026,4),None,0,0),
    ('立野FT',47600,False,ym(2026,4),None,0,10000),('佐々木FT',27200,False,ym(2026,4),None,0,20000),
    ('橋本FT',47600,False,ym(2026,4),None,17000,10000),('鶴川FT',47600,False,ym(2026,5),None,47600,0),
    ('吉田祥平FT',24000,False,ym(2026,6),None,0,0),('遠藤FT',34000,False,ym(2026,7),None,17000,0),
]
GL=108000;GL_KI=20000;TSURUMI=107800;TSURUMI_OKA=50000

work_months=[ym(2026,m) for m in range(4,13)]+[ym(2027,m) for m in range(1,4)]
pay_months=[ym(2026,m) for m in range(6,13)]+[ym(2027,m) for m in range(1,6)]

results={}
for pm in pay_months:
    results[pm]={b:{'terra':0,'ft':0,'gl':0,'choku':0,'oka_t':0,'oka_f':0,'oka_c':0,'ki_f':0,'ki_g':0} for b in ['15','matsu']}

for n,r,im,s,e,o in terra_eng:
    for wm in work_months:
        if not active(s,e,wm): continue
        pm=next2(wm)
        if pm not in results: continue
        b='matsu' if im else '15'
        ar,ao=r,o
        if n=='齋藤' and wm==ym(2026,5): ar=9150; ao=5494
        results[pm][b]['terra']+=ar; results[pm][b]['oka_t']+=ao

for n,r,im,s,e,o,k in ft_eng:
    for wm in work_months:
        if not active(s,e,wm): continue
        pm=next2(wm)
        if pm not in results: continue
        b='matsu' if im else '15'
        results[pm][b]['ft']+=r; results[pm][b]['oka_f']+=o; results[pm][b]['ki_f']+=k

for wm in work_months:
    pm=next2(wm)
    if pm in results: results[pm]['15']['gl']=GL; results[pm]['15']['ki_g']=GL_KI

for wm in work_months:
    if wm>=ym(2026,6):
        pm=next1(wm)
        if pm in results: results[pm]['matsu']['choku']=TSURUMI; results[pm]['matsu']['oka_c']=TSURUMI_OKA

row_map={}; r=5
for pm in pay_months: row_map[pm]={'15':r,'matsu':r+1,'sub':r+2}; r+=5

batch=[]
for pm in pay_months:
    for bucket in ['15','matsu']:
        row=row_map[pm][bucket]; d=results[pm][bucket]
        tr=d['terra'];gl_v=d['gl'];ft_v=d['ft'];ch=d['choku']
        oka=-(d['oka_t']+d['oka_f']+d['oka_c']); ki=-(d['ki_f']+d['ki_g'])
        gen=math.floor(tr*0.1021) if tr>0 else 0
        tzei=int(tr*1.1) if tr>0 else 0; tri=tzei-gen if tr>0 else 0
        gl_i=int(gl_v*1.1); ft_i=int(ft_v*1.1)
        sou=tri+gl_i+ft_i+ch+oka+ki
        for col,val in [(3,tr),(4,gen),(5,tzei),(6,tri),(7,gl_v),(8,ft_v),(9,ch),(10,oka),(11,ki),(12,sou)]:
            batch.append(gspread.Cell(row,col,val if val!=0 else '-'))
    sr=row_map[pm]['sub']; d15=results[pm]['15']; dma=results[pm]['matsu']
    s_tr=d15['terra']+dma['terra']
    s_gen=math.floor(d15['terra']*0.1021)+math.floor(dma['terra']*0.1021)
    s_tzei=int(d15['terra']*1.1)+int(dma['terra']*1.1); s_tri=s_tzei-s_gen
    s_gl=d15['gl']+dma['gl'];s_ft=d15['ft']+dma['ft'];s_ch=d15['choku']+dma['choku']
    s_oka=-(d15['oka_t']+d15['oka_f']+d15['oka_c']+dma['oka_t']+dma['oka_f']+dma['oka_c'])
    s_ki=-(d15['ki_f']+d15['ki_g']+dma['ki_f']+dma['ki_g'])
    s_gl_i=int(s_gl*1.1);s_ft_i=int(s_ft*1.1)
    s_sou=s_tri+s_gl_i+s_ft_i+s_ch+s_oka+s_ki
    for col,val in [(3,s_tr),(4,s_gen),(5,s_tzei),(6,s_tri),(7,s_gl),(8,s_ft),(9,s_ch if s_ch>0 else '-'),(10,s_oka),(11,s_ki),(12,s_sou)]:
        batch.append(gspread.Cell(sr,col,val))

ann=[0]*10
for pm in pay_months:
    sr=row_map[pm]['sub']
    for c in batch:
        if c.row==sr and 3<=c.col<=12:
            v=0 if c.value=='-' else int(c.value); ann[c.col-3]+=v
for i in range(10): batch.append(gspread.Cell(64,3+i,ann[i]))

print(f"Writing {len(batch)} cells to 入金予測...")
yosoku.update_cells(batch, value_input_option='RAW')

# Summary
print(f"\n{'月':>4} | {'総実入(源泉後)':>14} | {'額面(源泉前)':>12}")
print("-"*45)
ann_sou=0
for pm in pay_months:
    sr=row_map[pm]['sub']; vals={}
    for c in batch:
        if c.row==sr: vals[c.col]=0 if c.value=='-' else int(c.value)
    y,m=pm//100,pm%100
    gen=vals[4]
    sou=vals[12]
    gakumen=sou+gen
    print(f"{m}月".rjust(4)+f" | {sou:>14,} | {gakumen:>12,}")
    ann_sou+=sou
print("-"*45)
print(f"年間 | {ann_sou:>14,} |")
print(f"月平均| {ann_sou//12:>14,} |")
