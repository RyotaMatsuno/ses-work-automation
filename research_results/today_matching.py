import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3
import json

MATCH_DB = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3_processed.db"
conn = sqlite3.connect(MATCH_DB)
cur = conn.cursor()

# Today's cases with match details
cur.execute("""
    SELECT case_id, email_subject, business_status, match_results_json
    FROM processed_cases
    WHERE updated_at >= '2026-06-25'
    ORDER BY updated_at DESC
""")
rows = cur.fetchall()
print(f"=== TODAY'S MATCHING ({len(rows)} cases) ===\n")

match_counts = []
for cid, subj, status, results_json in rows:
    try:
        results = json.loads(results_json) if results_json else []
        cnt = len(results) if isinstance(results, list) else 0
    except:
        cnt = 0
    match_counts.append(cnt)

if match_counts:
    total = len(match_counts)
    has_match = sum(1 for m in match_counts if m > 0)
    print(f"Total cases: {total}")
    print(f"With matches: {has_match} ({has_match/total*100:.0f}%)")
    print(f"Zero matches: {total - has_match} ({(total-has_match)/total*100:.0f}%)")
    if has_match > 0:
        matched_only = [m for m in match_counts if m > 0]
        print(f"Avg matches (where >0): {sum(matched_only)/len(matched_only):.1f}")
    print(f"Overall avg: {sum(match_counts)/total:.1f}")
    print(f"Max: {max(match_counts)}")
    print(f"\nDistribution:")
    print(f"  0: {sum(1 for m in match_counts if m == 0)}")
    print(f"  1-3: {sum(1 for m in match_counts if 1 <= m <= 3)}")
    print(f"  4-10: {sum(1 for m in match_counts if 4 <= m <= 10)}")
    print(f"  11-50: {sum(1 for m in match_counts if 11 <= m <= 50)}")
    print(f"  50+: {sum(1 for m in match_counts if m > 50)}")

# Compare with historical (non-ERROR, all time)
print(f"\n=== HISTORICAL COMPARISON ===")
cur.execute("""
    SELECT match_results_json FROM processed_cases
    WHERE business_status != 'ERROR'
    AND updated_at < '2026-06-25'
""")
hist = cur.fetchall()
hist_counts = []
for (rj,) in hist:
    try:
        r = json.loads(rj) if rj else []
        hist_counts.append(len(r) if isinstance(r, list) else 0)
    except:
        hist_counts.append(0)

if hist_counts:
    h_total = len(hist_counts)
    h_match = sum(1 for m in hist_counts if m > 0)
    h_matched = [m for m in hist_counts if m > 0]
    print(f"Historical cases: {h_total}")
    print(f"Avg matches (where >0): {sum(h_matched)/len(h_matched):.1f}" if h_matched else "")
    print(f"Overall avg: {sum(hist_counts)/h_total:.1f}")
    print(f"50+: {sum(1 for m in hist_counts if m > 50)}")

conn.close()
