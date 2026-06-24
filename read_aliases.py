import json

aliases_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\skill_aliases.json"
with open(aliases_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"hard aliases: {len(data.get('aliases', {}))}")
print(f"soft aliases: {len(data.get('soft_aliases', {}))}")
print(f"soft_aliases_enabled: {data.get('soft_aliases_enabled')}")
print("\n=== hard aliases (全件) ===")
for k, v in sorted(data["aliases"].items()):
    print(f"  {k!r} -> {v!r}")
