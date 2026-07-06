import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3
import json
import os
from datetime import datetime, date

# 1. CostGuard
STATE_DB = r"C:\Users\ma_py\AppData\Local\ses_work_state\state.sqlite3"
conn = sqlite3.connect(STATE_DB)
cur = conn.cursor()

print("=== COSTGUARD ===")
# Today's cost
today = date.today().isoformat()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

for t in tables:
    cur.execute(f"PRAGMA table_info([{t}])")
    cols = [r[1] for r in cur.fetchall()]
    cur.execute(f"SELECT COUNT(*) FROM [{t}]")
    cnt = cur.fetchone()[0]
    if cnt > 0:
        print(f"\n  {t} ({cnt} rows): {cols}")
        if 'date' in cols or 'created_at' in cols or 'timestamp' in cols:
            date_col = 'date' if 'date' in cols else ('created_at' if 'created_at' in cols else 'timestamp')
            cur.execute(f"SELECT * FROM [{t}] ORDER BY [{date_col}] DESC LIMIT 5")
            for r in cur.fetchall():
                print(f"    {r}")
        else:
            cur.execute(f"SELECT * FROM [{t}] LIMIT 5")
            for r in cur.fetchall():
                print(f"    {r}")
conn.close()

# 2. Matching V3 - recent results
MATCH_DB = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3_processed.db"
conn2 = sqlite3.connect(MATCH_DB)
cur2 = conn2.cursor()

print("\n\n=== MATCHING V3 ===")

# Daily stats
cur2.execute("SELECT name FROM sqlite_master WHERE type='table'")
mtables = [r[0] for r in cur2.fetchall()]
print(f"Tables: {mtables}")

if 'daily_stats' in mtables:
    cur2.execute("SELECT * FROM daily_stats ORDER BY stat_date DESC LIMIT 10")
    rows = cur2.fetchall()
    print(f"\nDaily stats (last 10):")
    cur2.execute("PRAGMA table_info(daily_stats)")
    cols = [r[1] for r in cur2.fetchall()]
    print(f"  Columns: {cols}")
    for r in rows:
        print(f"  {r}")

# Today's processed cases
if 'processed_cases' in mtables:
    cur2.execute("PRAGMA table_info(processed_cases)")
    pcols = [r[1] for r in cur2.fetchall()]
    print(f"\nProcessed cases columns: {pcols}")
    
    # Recent cases
    date_col = None
    for c in ['processed_at', 'created_at', 'timestamp', 'date']:
        if c in pcols:
            date_col = c
            break
    
    if date_col:
        cur2.execute(f"SELECT * FROM processed_cases ORDER BY [{date_col}] DESC LIMIT 3")
        for r in cur2.fetchall():
            print(f"  Recent: {str(r)[:300]}")
    
    # Match count stats for recent
    if date_col and 'match_count' in pcols:
        cur2.execute(f"""
            SELECT COUNT(*) as total,
                   AVG(match_count) as avg_match,
                   SUM(CASE WHEN match_count = 0 THEN 1 ELSE 0 END) as zero_match,
                   MAX(match_count) as max_match,
                   MIN(match_count) as min_match
            FROM processed_cases
            WHERE [{date_col}] >= '2026-06-25'
        """)
        r = cur2.fetchone()
        print(f"\n  Today's matching:")
        print(f"    Total: {r[0]}, Avg: {r[1]}, Zero: {r[2]}, Max: {r[3]}, Min: {r[4]}")
    
    # Overall stats
    if 'match_count' in pcols:
        cur2.execute("""
            SELECT COUNT(*) as total,
                   AVG(match_count) as avg_match,
                   SUM(CASE WHEN match_count = 0 THEN 1 ELSE 0 END) as zero_match
            FROM processed_cases
            WHERE business_status != 'ERROR'
        """)
        r = cur2.fetchone()
        print(f"\n  Overall (non-ERROR):")
        print(f"    Total: {r[0]}, Avg: {r[1]:.1f}, Zero: {r[2]}")

# Check if hard_filters stats are logged somewhere
if 'filter_stats' in mtables:
    cur2.execute("SELECT * FROM filter_stats ORDER BY rowid DESC LIMIT 5")
    print(f"\nFilter stats:")
    for r in cur2.fetchall():
        print(f"  {r}")

conn2.close()
