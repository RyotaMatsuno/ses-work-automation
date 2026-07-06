import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

# 1. skill_aliases.json stats
aliases_path = Path("matching_v3/skill_aliases.json")
data = json.loads(aliases_path.read_text(encoding='utf-8'))
print("=== skill_aliases.json ===")
print(f"hard aliases: {len(data.get('aliases', {}))}")
print(f"soft_aliases: {len(data.get('soft_aliases', {}))}")
print(f"soft_aliases_enabled: {data.get('soft_aliases_enabled', False)}")
print(f"strict_alias_keys: {len(data.get('strict_alias_keys', []))}")
print(f"parent_skills: {len(data.get('parent_skills', {}))}")
print(f"skill_tiers: {len(data.get('skill_tiers', {}))}")
print(f"canonical_skills: {len(data.get('canonical_skills', []))}")

# 2. denylist.json stats
denylist_path = Path("matching_v3/denylist.json")
if denylist_path.exists():
    deny = json.loads(denylist_path.read_text(encoding='utf-8'))
    print("\n=== denylist.json ===")
    for k, v in deny.items():
        print(f"  {k}: {len(v)} entries")

# 3. Latest match_results.jsonl - last 20 entries
results_path = Path("matching_v3/logs/match_results.jsonl")
if results_path.exists():
    lines = results_path.read_text(encoding='utf-8').strip().splitlines()
    print(f"\n=== match_results.jsonl: {len(lines)} total entries ===")
    match_counts = []
    verdicts = {"MATCH": 0, "REVIEW": 0, "NG": 0, "PARTIAL_MATCH": 0}
    zero_match = 0
    for line in lines[-100:]:
        try:
            row = json.loads(line)
            mc = row.get("match_count", 0)
            match_counts.append(mc)
            if mc == 0:
                zero_match += 1
            for r in row.get("results", []):
                v = r.get("verdict", "")
                if v in verdicts:
                    verdicts[v] += 1
        except:
            pass
    print(f"  Last 100 entries avg_matches: {sum(match_counts)/max(len(match_counts),1):.2f}")
    print(f"  Last 100 zero-match rate: {zero_match}/{len(match_counts)} = {zero_match/max(len(match_counts),1)*100:.1f}%")
    print(f"  Verdicts: {verdicts}")

# 4. realtime worker log - last entries
rw_log = Path("matching_v3/logs/realtime_match_worker.log")
if rw_log.exists():
    rw_lines = rw_log.read_text(encoding='utf-8').strip().splitlines()
    print(f"\n=== realtime_match_worker.log: {len(rw_lines)} lines ===")
    for line in rw_lines[-15:]:
        print(f"  {line}")

# 5. Process skills that overlap with case required_skills
structured = Path("matching_v3/logs/structured.jsonl")
if structured.exists():
    process_skills = set(json.loads(Path("config/process_skills.json").read_text(encoding='utf-8')))
    all_required = []
    process_hits = []
    for line in structured.read_text(encoding='utf-8').strip().splitlines():
        try:
            row = json.loads(line)
            for s in row.get("required_skills", []):
                all_required.append(s)
                if s in process_skills:
                    process_hits.append(s)
        except:
            pass
    from collections import Counter
    print(f"\n=== Process skill overlap with case requirements ===")
    print(f"Total required skills in structured.jsonl: {len(all_required)}")
    print(f"Process skill hits (being excluded): {len(process_hits)} ({len(process_hits)/max(len(all_required),1)*100:.1f}%)")
    top_process = Counter(process_hits).most_common(20)
    print("Top 20 excluded process skills:")
    for skill, count in top_process:
        print(f"  {skill}: {count}")
