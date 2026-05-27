import re
path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline.py'
with open(path, encoding='utf-8') as f:
    content = f.read()

out = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\mail_pipeline_hits.txt'
hits = []
for m in re.finditer(r'anthropic|client\.messages|log_cost|usage', content, re.IGNORECASE):
    start = max(0, m.start()-80)
    hits.append(f"pos={m.start()}: ...{content[start:m.start()+150]}...")

with open(out, 'w', encoding='utf-8') as f:
    f.write('\n---\n'.join(hits))
print(f"{len(hits)} hits", flush=True)
