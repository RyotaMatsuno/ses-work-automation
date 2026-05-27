import re, os

for root, dirs, files in os.walk(r'C:\Users\ma_py\OneDrive'):
    if 'notify_line.py' in files:
        path = os.path.join(root, 'notify_line.py')
        with open(path, encoding='utf-8') as f:
            content = f.read()
        hits = [m.start() for m in re.finditer(r'anthropic|log_cost|Anthropic', content, re.IGNORECASE)]
        print(f"notify_line hits: {len(hits)}", flush=True)
        for pos in hits[:5]:
            print(content[max(0,pos-50):pos+100])
            print('---')
        break
