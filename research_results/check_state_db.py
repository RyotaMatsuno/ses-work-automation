import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3

# Check state.sqlite3
STATE_DB = r"C:\Users\ma_py\AppData\Local\ses_work_state\state.sqlite3"
conn = sqlite3.connect(STATE_DB)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("=== TABLES IN state.sqlite3 ===")
for r in cur.fetchall():
    name = r[0]
    cur2 = conn.cursor()
    cur2.execute(f"SELECT COUNT(*) FROM [{name}]")
    cnt = cur2.fetchone()[0]
    print(f"  {name} [{cnt} rows]")
conn.close()

# Check matching_v3_processed.db
MATCH_DB = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3_processed.db"
conn2 = sqlite3.connect(MATCH_DB)
cur2 = conn2.cursor()
cur2.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("\n=== TABLES IN matching_v3_processed.db ===")
for r in cur2.fetchall():
    name = r[0]
    c = conn2.cursor()
    c.execute(f"SELECT COUNT(*) FROM [{name}]")
    cnt = c.fetchone()[0]
    print(f"  {name} [{cnt} rows]")
    if cnt > 0:
        c.execute(f"PRAGMA table_info([{name}])")
        for col in c.fetchall():
            print(f"    - {col[1]} ({col[2]})")
conn2.close()
