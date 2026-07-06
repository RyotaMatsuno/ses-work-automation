import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3
import json

MATCH_DB = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3_processed.db"
conn = sqlite3.connect(MATCH_DB)
cur = conn.cursor()

# Get today's cases WITH matches
cur.execute("""
    SELECT case_id, email_subject, email_date, business_status, match_results_json, updated_at
    FROM processed_cases
    WHERE updated_at >= '2026-06-25'
    ORDER BY updated_at DESC
""")
rows = cur.fetchall()

print(f"=== TODAY'S MATCHING: {len(rows)} cases total ===\n")

matched_cases = []
for cid, subj, edate, status, results_json, updated in rows:
    try:
        results = json.loads(results_json) if results_json else []
        if not isinstance(results, list):
            results = []
    except:
        results = []
    
    if len(results) > 0:
        matched_cases.append({
            "case_id": cid,
            "subject": subj,
            "status": status,
            "match_count": len(results),
            "matches": results,
            "updated": updated
        })

print(f"Cases with matches: {len(matched_cases)}")
print(f"Cases with 0 matches: {len(rows) - len(matched_cases)}\n")

# Show ALL matched cases with their match details
for i, case in enumerate(matched_cases):
    print(f"{'='*70}")
    print(f"[案件{i+1}] {case['subject']}")
    print(f"  status: {case['status']} | matches: {case['match_count']}")
    print(f"  case_id: {case['case_id']}")
    
    for j, match in enumerate(case['matches']):
        eng_id = match.get('engineer_id', '?')
        eng_init = match.get('engineer_initial', '?')
        verdict = match.get('verdict', '?')
        reasons = match.get('reasons', [])
        score = match.get('score', '?')
        
        print(f"  [{j+1}] {eng_init} | verdict={verdict} | score={score}")
        if reasons:
            for r in reasons[:5]:
                print(f"      - {r}")
    print()

conn.close()
