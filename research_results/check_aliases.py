import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import json

# Examine skill_aliases.json structure
ALIAS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\skill_aliases.json"
with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
    aliases = json.load(f)

print(f"=== SKILL_ALIASES.JSON STRUCTURE ===")
print(f"Top-level keys: {len(aliases)}")
print(f"Type of first value: {type(list(aliases.values())[0])}")
print()

# Show all keys and their alias count
for k, v in aliases.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)} aliases")
    elif isinstance(v, dict):
        print(f"  {k}: {len(v)} sub-keys")
        # Show sub-structure
        for sk, sv in list(v.items())[:3]:
            print(f"    {sk}: {sv}")
    else:
        print(f"  {k}: {v}")

# Count total unique alias strings
all_aliases = set()
for k, v in aliases.items():
    if isinstance(v, list):
        for a in v:
            if isinstance(a, str):
                all_aliases.add(a.lower())
            elif isinstance(a, dict):
                for dk, dv in a.items():
                    all_aliases.add(dk.lower())
    elif isinstance(v, dict):
        for sk, sv in v.items():
            all_aliases.add(sk.lower())
            if isinstance(sv, list):
                for a in sv:
                    all_aliases.add(a.lower())

print(f"\nTotal unique alias strings: {len(all_aliases)}")
