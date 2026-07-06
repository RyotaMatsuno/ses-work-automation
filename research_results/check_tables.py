import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import sqlite3
import os

DB_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\raw_inbox.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("=== TABLES IN raw_inbox.db ===")
for r in cur.fetchall():
    print(f"  {r[0]}")
    # Show columns
    cur2 = conn.cursor()
    cur2.execute(f"PRAGMA table_info({r[0]})")
    cols = cur2.fetchall()
    for c in cols:
        print(f"    - {c[1]} ({c[2]})")
    cur2.execute(f"SELECT COUNT(*) FROM {r[0]}")
    cnt = cur2.fetchone()[0]
    print(f"    [rows: {cnt}]")
conn.close()
