with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\matching_v2.py', encoding='utf-8') as f:
    content = f.read()
# Claude API呼び出し箇所を探す
import re
hits = [(m.start(), content[max(0,m.start()-100):m.start()+200]) for m in re.finditer(r'client\.messages\.create|anthropic\.Anthropic|usage', content)]
for i, (pos, snippet) in enumerate(hits[:10]):
    print(f"--- hit {i} pos={pos} ---")
    print(snippet)
    print()
