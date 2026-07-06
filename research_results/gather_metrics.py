import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3
import json
import os

DB_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\raw_inbox.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# 1. Total records
cur.execute("SELECT COUNT(*) FROM structured_projects")
total = cur.fetchone()[0]
print(f"=== STRUCTURED_PROJECTS TOTAL: {total} ===")

# 2. Status breakdown
cur.execute("SELECT status, COUNT(*) as cnt FROM structured_projects GROUP BY status ORDER BY cnt DESC")
print("\n--- STATUS BREAKDOWN ---")
for r in cur.fetchall():
    print(f"  {r['status']}: {r['cnt']}")

# 3. Key field emptiness
fields = ['required_skills', 'preferred_skills', 'rate_min', 'rate_max', 'location', 'role']
for f in fields:
    cur.execute(f"SELECT COUNT(*) FROM structured_projects WHERE status='募集中' AND ({f} IS NULL OR {f} = '' OR {f} = '[]' OR {f} = 'null')")
    empty = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM structured_projects WHERE status='募集中'")
    active = cur.fetchone()[0]
    pct = (empty / active * 100) if active > 0 else 0
    print(f"  {f} empty (募集中): {empty}/{active} = {pct:.1f}%")

# 4. Skills quality check - what % have >=2 skills
cur.execute("""
    SELECT COUNT(*) FROM structured_projects 
    WHERE status='募集中' 
    AND required_skills IS NOT NULL 
    AND required_skills != '' 
    AND required_skills != '[]'
""")
has_skills = cur.fetchone()[0]
print(f"\n--- SKILLS QUALITY ---")
print(f"  Has required_skills: {has_skills}/{active}")

# Check how many have proper JSON array with 2+ items
cur.execute("""
    SELECT required_skills FROM structured_projects 
    WHERE status='募集中' 
    AND required_skills IS NOT NULL 
    AND required_skills != '' 
    AND required_skills != '[]'
""")
skill_counts = []
for r in cur.fetchall():
    try:
        skills = json.loads(r[0]) if r[0] else []
        if isinstance(skills, list):
            skill_counts.append(len(skills))
    except:
        skill_counts.append(0)

if skill_counts:
    print(f"  Avg skills per project: {sum(skill_counts)/len(skill_counts):.1f}")
    print(f"  1 skill only: {sum(1 for s in skill_counts if s == 1)}")
    print(f"  2-3 skills: {sum(1 for s in skill_counts if 2 <= s <= 3)}")
    print(f"  4+ skills: {sum(1 for s in skill_counts if s >= 4)}")

# 5. Rate quality
cur.execute("""
    SELECT rate_min, rate_max FROM structured_projects 
    WHERE status='募集中' 
    AND (rate_min IS NOT NULL AND rate_min != '')
""")
rates = cur.fetchall()
rate_vals = []
for r in rates:
    try:
        v = float(r[0]) if r[0] else 0
        if v > 0:
            rate_vals.append(v)
    except:
        pass
if rate_vals:
    print(f"\n--- RATE QUALITY ---")
    print(f"  Has rate: {len(rate_vals)}/{active}")
    print(f"  Avg rate_min: {sum(rate_vals)/len(rate_vals):.0f}万")
    print(f"  Rate < 30万: {sum(1 for v in rate_vals if v < 30)}")
    print(f"  Rate 30-50万: {sum(1 for v in rate_vals if 30 <= v < 50)}")
    print(f"  Rate 50-80万: {sum(1 for v in rate_vals if 50 <= v <= 80)}")
    print(f"  Rate > 80万: {sum(1 for v in rate_vals if v > 80)}")
    print(f"  Rate > 200万 (anomaly): {sum(1 for v in rate_vals if v > 200)}")

# 6. Preferred skills quality
cur.execute("""
    SELECT COUNT(*) FROM structured_projects 
    WHERE status='募集中' 
    AND preferred_skills IS NOT NULL 
    AND preferred_skills != '' 
    AND preferred_skills != '[]'
    AND preferred_skills != 'null'
""")
has_pref = cur.fetchone()[0]
print(f"\n--- PREFERRED SKILLS ---")
print(f"  Has preferred_skills: {has_pref}/{active} = {has_pref/active*100:.1f}%")

# 7. Location quality
cur.execute("""
    SELECT location, COUNT(*) as cnt FROM structured_projects 
    WHERE status='募集中' 
    AND location IS NOT NULL AND location != ''
    GROUP BY location ORDER BY cnt DESC LIMIT 15
""")
print(f"\n--- TOP LOCATIONS ---")
for r in cur.fetchall():
    print(f"  {r['location']}: {r['cnt']}")

# 8. ERROR records
cur.execute("SELECT COUNT(*) FROM structured_projects WHERE status='ERROR'")
errors = cur.fetchone()[0]
print(f"\n--- ERRORS ---")
print(f"  ERROR records: {errors}")

# 9. Matching results from matching_v3
MATCH_DB = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3_processed.db"
if os.path.exists(MATCH_DB):
    mconn = sqlite3.connect(MATCH_DB)
    mcur = mconn.cursor()
    try:
        mcur.execute("SELECT COUNT(*) FROM processed_cases")
        total_processed = mcur.fetchone()[0]
        mcur.execute("SELECT COUNT(*) FROM processed_cases WHERE match_count > 0")
        has_match = mcur.fetchone()[0]
        mcur.execute("SELECT AVG(match_count) FROM processed_cases WHERE match_count > 0")
        avg_match = mcur.fetchone()[0]
        print(f"\n--- MATCHING V3 RESULTS ---")
        print(f"  Total processed: {total_processed}")
        print(f"  Has matches: {has_match} ({has_match/total_processed*100:.1f}%)")
        print(f"  Avg match count (where >0): {avg_match:.1f}")
    except Exception as e:
        print(f"  Matching DB error: {e}")
    mconn.close()

# 10. Skill dictionary size
ALIAS_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\skill_aliases.json"
if os.path.exists(ALIAS_PATH):
    with open(ALIAS_PATH, 'r', encoding='utf-8') as f:
        aliases = json.load(f)
    canonical = len(aliases)
    total_aliases = sum(len(v) if isinstance(v, list) else 1 for v in aliases.values())
    print(f"\n--- SKILL DICTIONARY ---")
    print(f"  Canonical skills: {canonical}")
    print(f"  Total aliases: {total_aliases}")

conn.close()
print("\n=== DONE ===")
