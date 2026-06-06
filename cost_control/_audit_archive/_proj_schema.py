import sys, json, requests, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
KEY = cfg.get("NOTION_API_KEY")
DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
H = {"Authorization": f"Bearer {KEY}", "Notion-Version":"2022-06-28","Content-Type":"application/json"}
out=[]
def w(*a): out.append(" ".join(str(x) for x in a))

# schema
r=requests.get(f"https://api.notion.com/v1/databases/{DB}",headers=H,timeout=30)
w("schema status",r.status_code)
props=r.json().get("properties",{})
status_prop=None; date_props=[]
for n,p in props.items():
    t=p.get("type")
    w(f"  PROP {n} ({t})")
    if t in ("status","select"):
        opts=[o.get("name") for o in (p.get(t,{}).get("options",[]))]
        w(f"     options: {opts}")
        if any(k in n for k in ["ステータス","状態","status","Status"]): status_prop=(n,t,opts)
    if t in ("date","created_time"): date_props.append((n,t))
w("STATUS_PROP=",status_prop)
w("DATE_PROPS=",date_props)

# paginate, collect status + best date
def getval(props,name,typ):
    v=props.get(name,{})
    if typ=="status": return (v.get("status") or {}).get("name")
    if typ=="select": return (v.get("select") or {}).get("name")
    if typ=="date": return (v.get("date") or {}).get("start")
    if typ=="created_time": return v.get("created_time")
    return None

rows=[]; cursor=None; pages=0
while True:
    body={"page_size":100}
    if cursor: body["start_cursor"]=cursor
    rr=requests.post(f"https://api.notion.com/v1/databases/{DB}/query",headers=H,json=body,timeout=60)
    if rr.status_code!=200:
        w("query err",rr.status_code,rr.text[:200]); break
    d=rr.json(); rows.extend(d.get("results",[])); pages+=1
    if not d.get("has_more"): break
    cursor=d.get("next_cursor")
    if pages>80: w("PAGE CAP hit"); break
w("total_rows",len(rows),"pages",pages)

today=datetime.date(2026,6,5)
# pick primary date prop: prefer a 'date'-typed named like 受信/登録/作成, else created_time
prefer=None
for n,t in date_props:
    if any(k in n for k in ["受信","登録","作成","日付","date","Date"]) and t=="date": prefer=(n,t);break
if not prefer and date_props: prefer=date_props[0]
w("PRIMARY_DATE=",prefer)

from collections import Counter
status_ct=Counter(); age_buckets=Counter(); status_stale=Counter()
sname=status_prop[0] if status_prop else None
stype=status_prop[1] if status_prop else None
no_date=0
for r0 in rows:
    pr=r0.get("properties",{})
    st=getval(pr,sname,stype) if sname else "(no status prop)"
    status_ct[st]+=1
    ds=getval(pr,prefer[0],prefer[1]) if prefer else None
    if not ds:
        no_date+=1; continue
    try:
        dd=datetime.date.fromisoformat(ds[:10])
        age=(today-dd).days
    except: 
        no_date+=1; continue
    b = "0-3d" if age<=3 else "4-6d" if age<=6 else "7-13d" if age<=13 else "14-30d" if age<=30 else "31d+"
    age_buckets[b]+=1
    if age>=7:  # clearly stale (>1 week)
        status_stale[st]+=1

w("\n=== STATUS histogram ===")
for k,v in status_ct.most_common(): w(f"  {k}: {v}")
w("\n=== AGE histogram (by primary date) ===")
for k in ["0-3d","4-6d","7-13d","14-30d","31d+"]:
    if age_buckets[k]: w(f"  {k}: {age_buckets[k]}")
w(f"  (date欠損: {no_date})")
w("\n=== >=7日(明確にstale) の status内訳 ===")
for k,v in status_stale.most_common(): w(f"  {k}: {v}")
w(f"  >=7日 合計: {sum(status_stale.values())}")

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_proj_schema.txt","w",encoding="utf-8") as f:
    f.write("\n".join(str(x) for x in out))
print("DONE rows",len(rows))
