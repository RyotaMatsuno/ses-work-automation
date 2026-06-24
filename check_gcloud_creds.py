import json
import os
import sqlite3

db_path = os.path.expandvars(r"%APPDATA%\gcloud\credentials.db")
conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT * FROM credentials").fetchall()
print(f"credentials.db rows: {len(rows)}")
for r in rows:
    print(f"  account: {r[0]}")
    try:
        data = json.loads(r[1])
        keys = list(data.keys())
        print(f"  keys: {keys}")
        if "token_uri" in data:
            print(f"  token_uri: {data['token_uri']}")
        if "scopes" in data:
            print(f"  scopes: {data['scopes']}")
        if "refresh_token" in data:
            print("  refresh_token: present")
        if "client_id" in data:
            print(f"  client_id: {data['client_id'][:40]}")
        if "client_secret" in data:
            print("  client_secret: present!")
    except:
        print(f"  raw: {str(r[1])[:100]}")
conn.close()
