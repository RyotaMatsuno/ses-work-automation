import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3
import json

# matching_v3 detailed metrics
MATCH_DB = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3_processed.db"
conn = sqlite3.connect(MATCH_DB)
cur = conn.cursor()

print("=== MATCHING V3 DETAILED METRICS ===")

# Total processed
cur.execute("SELECT COUNT(*) FROM processed_cases")
total = cur.fetchone()[0]
print(f"Total processed: {total}")

# Business status breakdown
cur.execute("SELECT business_status, COUNT(*) FROM processed_cases GROUP BY business_status ORDER BY COUNT(*) DESC")
print("\nBusiness status:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Match count distribution
cur.execute("SELECT COUNT(*) FROM processed_cases WHERE match_results_json IS NOT NULL AND match_results_json != ''")
has_results = cur.fetchone()[0]

# Parse match results
cur.execute("SELECT match_results_json FROM processed_cases WHERE match_results_json IS NOT NULL AND match_results_json != ''")
match_counts = []
zero_matches = 0
for r in cur.fetchall():
    try:
        data = json.loads(r[0])
        if isinstance(data, list):
            cnt = len(data)
        elif isinstance(data, dict):
            cnt = data.get('match_count', 0)
            if 'matches' in data:
                cnt = len(data['matches'])
        else:
            cnt = 0
        match_counts.append(cnt)
        if cnt == 0:
            zero_matches += 1
    except:
        match_counts.append(0)
        zero_matches += 1

if match_counts:
    total_m = len(match_counts)
    has_match = sum(1 for m in match_counts if m > 0)
    print(f"\nMatch distribution ({total_m} cases with results):")
    print(f"  0 matches: {zero_matches} ({zero_matches/total_m*100:.1f}%)")
    print(f"  1-3 matches: {sum(1 for m in match_counts if 1 <= m <= 3)}")
    print(f"  4-10 matches: {sum(1 for m in match_counts if 4 <= m <= 10)}")
    print(f"  11-50 matches: {sum(1 for m in match_counts if 11 <= m <= 50)}")
    print(f"  50+ matches: {sum(1 for m in match_counts if m > 50)}")
    print(f"  MATCH rate: {has_match/total_m*100:.1f}%")
    if has_match > 0:
        matched_only = [m for m in match_counts if m > 0]
        print(f"  Avg matches (where >0): {sum(matched_only)/len(matched_only):.1f}")
    print(f"  Overall avg: {sum(match_counts)/total_m:.1f}")

# Daily stats
cur.execute("SELECT * FROM daily_stats ORDER BY stat_date DESC LIMIT 10")
print("\nDaily stats (last 10):")
for r in cur.fetchall():
    print(f"  {r[0]}: calls={r[1]}, cost=${r[2]:.2f}, matches={r[5]}")

# Cost
cur.execute("SELECT SUM(total_cost_usd) FROM processed_cases")
total_cost = cur.fetchone()[0]
print(f"\nTotal matching cost: ${total_cost:.2f}")

conn.close()

# Skill dictionary
ALIAS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\skill_aliases.json"
with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
    aliases = json.load(f)
canonical = len(aliases)
total_aliases = sum(len(v) if isinstance(v, list) else 1 for v in aliases.values())
print(f"\n=== SKILL DICTIONARY ===")
print(f"Canonical: {canonical}, Aliases: {total_aliases}")

# Raw emails classification
RAW_DB = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\raw_inbox.db"
conn2 = sqlite3.connect(RAW_DB)
cur2 = conn2.cursor()
cur2.execute("SELECT classify_result, COUNT(*) FROM raw_emails WHERE classify_result IS NOT NULL GROUP BY classify_result ORDER BY COUNT(*) DESC")
print(f"\n=== CLASSIFICATION BREAKDOWN ===")
for r in cur2.fetchall():
    print(f"  {r[0]}: {r[1]}")

# Error count
cur2.execute("SELECT COUNT(*) FROM raw_emails WHERE classify_result = 'ERROR'")
err_cnt = cur2.fetchone()[0]
print(f"\n  ERROR total: {err_cnt}")

# How many processed=1 vs 0
cur2.execute("SELECT processed, COUNT(*) FROM raw_emails GROUP BY processed")
print(f"\n  Processed flag:")
for r in cur2.fetchall():
    print(f"    processed={r[0]}: {r[1]}")

conn2.close()
print("\n=== DATA GATHERING DONE ===")
