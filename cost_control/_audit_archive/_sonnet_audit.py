import sys, os, re, glob
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
out=[]
def w(*a): out.append(" ".join(str(x) for x in a))

# Files that actually run in production and may use Sonnet/vision
targets = [
    "mail_pipeline/mail_pipeline.py",
    "mail_attachment_importer/importer.py",
    "mail_attachment_importer/ai_extractor.py",
    "mail_attachment_importer/text_parser.py",
    "outlook_to_notion.py",
    "matching_v2/skill_judge.py",
    "matching_v3/config.py",
    "matching_v3/structurer.py",
]
# also glob for any file mentioning sonnet
sonnet_files = set()
for p in glob.glob(os.path.join(BASE,"**","*.py"),recursive=True):
    if ".git" in p: continue
    try: t=open(p,encoding="utf-8",errors="replace").read()
    except: continue
    if "sonnet" in t.lower():
        sonnet_files.add(p)

w("=== files mentioning 'sonnet' ===")
for p in sorted(sonnet_files):
    rel=p.replace(BASE,"")
    # show only non-test, prod-ish
    cnt=open(p,encoding="utf-8",errors="replace").read().lower().count("sonnet")
    w(f"  {rel}  (sonnet x{cnt})")

def show_model_logic(rel):
    p=os.path.join(BASE,rel)
    if not os.path.exists(p):
        w(f"\n--- {rel}: NOT FOUND"); return
    t=open(p,encoding="utf-8",errors="replace").read()
    lines=t.splitlines()
    w(f"\n--- {rel} ({len(lines)} lines) ---")
    # model decision + vision/pdf branch keywords
    KW=["sonnet","haiku","gpt-","DEFAULT_","_MODEL","model =","model=","\"model\"","'model'",
        "image","media_type","base64","pdf","PDF","vision","添付","attachment","ocr","OCR",
        "xlsx","openpyxl","pdfplumber","docx","extract","classify_content","def classify","判定モデル"]
    seen=set()
    for i,l in enumerate(lines,1):
        s=l.strip()
        if s.startswith("#"): continue
        for kw in KW:
            if kw in l:
                if i in seen: break
                seen.add(i)
                w(f"  {i}: {s[:130]}")
                break

for rel in targets:
    show_model_logic(rel)

with open(os.path.join(BASE,"_sonnet_audit.txt"),"w",encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("DONE")
