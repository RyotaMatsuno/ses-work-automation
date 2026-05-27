# -*- coding: utf-8 -*-
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

data = json.load(open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\result.json', encoding='utf-8'))
print(f'result.json: {len(data)}件')
if data:
    item = data[0]
    print(f'keys: {list(item.keys())}')
    print(f'raw_body: "{item.get("raw_body","(なし)")[:100]}"')
    if item.get('candidates'):
        c = item['candidates'][0]
        print(f'candidate keys: {list(c.keys())}')
        print(f'candidate raw_body: "{c.get("raw_body","(なし)")[:100]}"')
