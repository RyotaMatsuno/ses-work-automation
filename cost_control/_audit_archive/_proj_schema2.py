import sys, json, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from dotenv import dotenv_values
cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
KEY=cfg.get("NOTION_API_KEY")
DB="343450ff-37c0-81e4-934e-f25f90284a3c"
H={"Authorization":f"Bearer {KEY}","Notion-Version":"2022-06-28","Content-Type":"application/json"}
out=[]
def w(*a): out.append(" ".join(str(x) for x in a))
r=requests.get(f"https://api.notion.com/v1/databases/{DB}",headers=H,timeout=30)
w("schema status",r.status_code)
props=r.json().get("properties",{})
for n,p in props.items():
    t=p.get("type")
    line=f"PROP {n} ({t})"
    if t in ("status","select"):
        line += " :: " + str([o.get("name") for o in p.get(t,{}).get("options",[])])
    w(line)
# 1 sample row to see date fields populated
rr=requests.post(f"https://api.notion.com/v1/databases/{DB}/query",headers=H,json={"page_size":3},timeout=30)
w("\nsample status",rr.status_code)
for res in rr.json().get("results",[])[:3]:
    pr=res.get("properties",{})
    flat={}
    for k,v in pr.items():
        t=v.get("type")
        if t=="title": flat[k]="".join(x.get("plain_text","") for x in v.get("title",[]))[:30]
        elif t=="status": flat[k]=(v.get("status") or {}).get("name")
        elif t=="select": flat[k]=(v.get("select") or {}).get("name")
        elif t=="date": flat[k]=(v.get("date") or {}).get("start")
        elif t=="created_time": flat[k]=v.get("created_time")
    w("  created_time(meta):",res.get("created_time"))
    w("  ROW:",json.dumps(flat,ensure_ascii=False)[:300])
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\_proj_schema.txt","w",encoding="utf-8") as f:
    f.write("\n".join(str(x) for x in out))
print("DONE")
