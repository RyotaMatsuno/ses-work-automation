import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
import json

base = os.path.dirname(os.path.abspath(__file__))

# 1. List extractors directory
ext_dir = os.path.join(base, 'extractors')
print("=== EXTRACTORS ===")
if os.path.exists(ext_dir):
    for f in os.listdir(ext_dir):
        fpath = os.path.join(ext_dir, f)
        size = os.path.getsize(fpath)
        print(f"  {f} ({size} bytes)")
else:
    print("  extractors/ not found")

# 2. Check matching_v3 structure
m3_dir = os.path.join(base, 'matching_v3')
print("\n=== MATCHING_V3 ===")
if os.path.exists(m3_dir):
    for f in sorted(os.listdir(m3_dir)):
        fpath = os.path.join(m3_dir, f)
        if os.path.isfile(fpath):
            size = os.path.getsize(fpath)
            print(f"  {f} ({size} bytes)")
        else:
            print(f"  {f}/ (dir)")

# 3. Check research_results for GPT wallhit files
res_dir = os.path.join(base, 'research_results')
print("\n=== RESEARCH_RESULTS ===")
if os.path.exists(res_dir):
    for f in sorted(os.listdir(res_dir)):
        if 'commercial' in f.lower() or 'matching' in f.lower() or 'quality' in f.lower():
            print(f"  {f}")
else:
    print("  research_results/ not found")

# 4. Check pending_tasks
pt_dir = os.path.join(base, 'pending_tasks')
print("\n=== PENDING_TASKS ===")
if os.path.exists(pt_dir):
    files = os.listdir(pt_dir)
    print(f"  {len(files)} files")
    for f in sorted(files)[-5:]:
        print(f"  {f}")
else:
    print("  pending_tasks/ not found")

# 5. Check skill_aliases.json
sa_path = os.path.join(base, 'matching_v3', 'skill_aliases.json')
print("\n=== SKILL_ALIASES ===")
if os.path.exists(sa_path):
    with open(sa_path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)
    print(f"  {len(data)} aliases loaded")
else:
    print("  not found")
