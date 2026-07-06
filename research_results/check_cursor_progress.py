import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json
import os

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 1. Check batch_remaining.json (largest backfill log)
bl = os.path.join(SES, "backfill_logs", "batch_remaining.json")
with open(bl, 'r', encoding='utf-8') as f:
    data = json.load(f)

if isinstance(data, list):
    print(f"=== BATCH_REMAINING: {len(data)} records ===")
    # Count by status
    success = sum(1 for d in data if d.get("status") == "success" or d.get("changes"))
    error = sum(1 for d in data if d.get("status") == "error" or d.get("error"))
    skipped = sum(1 for d in data if d.get("status") == "skipped" or d.get("skipped"))
    print(f"  Success: {success}")
    print(f"  Error: {error}")
    print(f"  Skipped: {skipped}")
    # Sample first entry
    if data:
        print(f"\n  Sample entry keys: {list(data[0].keys())}")
        print(f"  Sample: {json.dumps(data[0], ensure_ascii=False)[:300]}")
elif isinstance(data, dict):
    print(f"=== BATCH_REMAINING (dict) ===")
    print(f"  Keys: {list(data.keys())}")
    if 'results' in data:
        print(f"  Results count: {len(data['results'])}")
    if 'summary' in data:
        print(f"  Summary: {json.dumps(data['summary'], ensure_ascii=False)[:500]}")

# 2. Check hard_filters.py content
hf = os.path.join(SES, "matching_v3", "hard_filters.py")
with open(hf, 'r', encoding='utf-8') as f:
    content = f.read()
print(f"\n=== HARD_FILTERS.PY ({len(content)} bytes) ===")
# Show function names
import re
funcs = re.findall(r'def (\w+)\(', content)
print(f"  Functions: {funcs}")
# Show key classes
classes = re.findall(r'class (\w+)', content)
print(f"  Classes: {classes}")
# Check if it's integrated into matching_v3.py
m3 = os.path.join(SES, "matching_v3", "matching_v3.py")
with open(m3, 'r', encoding='utf-8') as f:
    m3content = f.read()
if 'hard_filters' in m3content or 'hard_filter' in m3content:
    print(f"  Integrated into matching_v3.py: YES")
else:
    print(f"  Integrated into matching_v3.py: NO")

# 3. Check config.py HARD_FILTERS
cfg = os.path.join(SES, "matching_v3", "config.py")
with open(cfg, 'r', encoding='utf-8') as f:
    cfgcontent = f.read()
# Extract HARD_FILTERS
hf_match = re.search(r'HARD_FILTERS\s*=\s*\{[^}]+\}', cfgcontent, re.DOTALL)
if hf_match:
    print(f"\n=== CONFIG HARD_FILTERS ===")
    print(f"  {hf_match.group()}")
