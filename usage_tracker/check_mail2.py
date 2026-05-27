import re, glob, os

# ses_workのフルパスを動的に取得
base = None
for root, dirs, files in os.walk(r'C:\Users\ma_py\OneDrive'):
    if 'mail_pipeline.py' in files:
        base = root
        break

if base:
    path = os.path.join(base, 'mail_pipeline.py')
    print(f"found: {path}", flush=True)
    with open(path, encoding='utf-8') as f:
        content = f.read()
    hits = []
    for m in re.finditer(r'anthropic|client\.messages|log_cost|Anthropic', content, re.IGNORECASE):
        start = max(0, m.start()-60)
        hits.append(f"pos={m.start()}: {content[start:m.start()+120]}")
    print(f"{len(hits)} hits", flush=True)
    for h in hits[:10]:
        print(h)
        print('---')
else:
    print("not found", flush=True)
