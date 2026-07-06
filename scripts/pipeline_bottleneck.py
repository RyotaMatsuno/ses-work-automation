import sys, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
from collections import Counter

# Load all data
aliases_data = json.loads(Path("matching_v3/skill_aliases.json").read_text(encoding='utf-8'))
hard_aliases = {k.lower(): v for k, v in aliases_data.get("aliases", {}).items()}
process_skills = set(json.loads(Path("config/process_skills.json").read_text(encoding='utf-8')))
soft_skills_list = json.loads(Path("config/soft_skills.json").read_text(encoding='utf-8'))
soft_skills = {s.lower() for s in soft_skills_list}

# Load structured cases
structured = Path("matching_v3/logs/structured.jsonl")
cases = []
for line in structured.read_text(encoding='utf-8').strip().splitlines():
    try:
        cases.append(json.loads(line))
    except:
        pass

print(f"Total structured cases: {len(cases)}")

# Analyze each case's required_skills pipeline
stats = {
    "total_cases": len(cases),
    "no_required_skills": 0,
    "all_skills_removed": 0,  # All skills are process/soft
    "all_skills_oov": 0,  # All remaining skills are OOV (not in alias dict)
    "has_matchable_skills": 0,
    "avg_required_count": 0,
    "avg_tech_after_filter": 0,
    "avg_resolved_after_alias": 0,
}

oov_skills = Counter()
removed_skills = Counter()
all_required_counts = []
tech_counts = []
resolved_counts = []

for case in cases:
    required = case.get("required_skills", [])
    all_required_counts.append(len(required))
    
    if not required:
        stats["no_required_skills"] += 1
        continue
    
    # Step 1: Remove soft skills
    after_soft = []
    for s in required:
        s_lower = s.lower().strip()
        is_soft = any(ss in s_lower for ss in soft_skills if len(ss) >= 2)
        if not is_soft:
            after_soft.append(s)
        else:
            removed_skills[s] += 1
    
    # Step 2: Remove process skills (competencies)
    tech_only = []
    for s in after_soft:
        s_stripped = s.strip()
        # Check exact match in process_skills
        if s_stripped in process_skills:
            removed_skills[s_stripped] += 1
        else:
            tech_only.append(s)
    
    tech_counts.append(len(tech_only))
    
    if not tech_only:
        stats["all_skills_removed"] += 1
        continue
    
    # Step 3: Resolve via alias dictionary
    resolved = []
    for s in tech_only:
        key = " ".join(s.lower().strip().split())
        if key in hard_aliases:
            resolved.append(hard_aliases[key])
        else:
            # Check if it's a known canonical
            found = False
            for canon in aliases_data.get("canonical_skills", []):
                if canon.lower() == key:
                    resolved.append(canon)
                    found = True
                    break
            if not found:
                oov_skills[s] += 1
    
    resolved_counts.append(len(resolved))
    
    if not resolved:
        stats["all_skills_oov"] += 1
    else:
        stats["has_matchable_skills"] += 1

stats["avg_required_count"] = sum(all_required_counts) / max(len(all_required_counts), 1)
stats["avg_tech_after_filter"] = sum(tech_counts) / max(len(tech_counts), 1)
stats["avg_resolved_after_alias"] = sum(resolved_counts) / max(len(resolved_counts), 1)

print("\n=== Pipeline Bottleneck Analysis ===")
for k, v in stats.items():
    if isinstance(v, float):
        print(f"  {k}: {v:.2f}")
    else:
        print(f"  {k}: {v}")

pct_no_skills = stats["no_required_skills"] / max(stats["total_cases"], 1) * 100
pct_all_removed = stats["all_skills_removed"] / max(stats["total_cases"], 1) * 100
pct_all_oov = stats["all_skills_oov"] / max(stats["total_cases"], 1) * 100
pct_matchable = stats["has_matchable_skills"] / max(stats["total_cases"], 1) * 100

print(f"\n=== Conversion Funnel ===")
print(f"  Input cases: {stats['total_cases']} (100%)")
print(f"  -> No required skills: {stats['no_required_skills']} ({pct_no_skills:.1f}%)")
print(f"  -> All skills removed (process/soft): {stats['all_skills_removed']} ({pct_all_removed:.1f}%)")
print(f"  -> All remaining OOV: {stats['all_skills_oov']} ({pct_all_oov:.1f}%)")
print(f"  -> HAS MATCHABLE SKILLS: {stats['has_matchable_skills']} ({pct_matchable:.1f}%)")

print(f"\n=== Top 30 OOV Skills (not in alias dict) ===")
for skill, count in oov_skills.most_common(30):
    print(f"  {skill}: {count}")

print(f"\n=== Top 20 Removed Skills (process/soft) ===")
for skill, count in removed_skills.most_common(20):
    print(f"  {skill}: {count}")

# Engineer side analysis
# Check what % of engineers have skills in the alias dictionary
print(f"\n=== OOV Analysis Summary ===")
print(f"Total unique OOV skills: {len(oov_skills)}")
print(f"Total OOV occurrences: {sum(oov_skills.values())}")
total_tech = sum(tech_counts)
total_resolved = sum(resolved_counts)
print(f"Total tech skills (after process/soft removal): {total_tech}")
print(f"Total resolved (in alias dict): {total_resolved}")
print(f"Resolution rate: {total_resolved/max(total_tech,1)*100:.1f}%")
