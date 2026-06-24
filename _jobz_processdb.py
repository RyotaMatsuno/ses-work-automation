import glob
import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(os.getcwd())
today = date.today().strftime("%Y%m%d")

# ProcessedDB の実体を探す
print("■ ProcessedDB ファイル探索")
for root, dirs, files in os.walk(SES / "matching_v3"):
    dirs[:] = [d for d in dirs if d not in ["__pycache__"]]
    for fn in files:
        if fn.endswith((".db", ".sqlite", ".sqlite3", ".json")) and "process" in fn.lower():
            fp = os.path.join(root, fn)
            print(f"  発見: {os.path.relpath(fp, SES)} ({os.path.getsize(fp)}b)")

# processed.db があればSQLiteで確認
for db_path in glob.glob(str(SES / "matching_v3" / "**" / "*.db"), recursive=True):
    print(f"\n■ {os.path.relpath(db_path, SES)}")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # テーブル一覧
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"  テーブル: {tables}")
        for t in tables:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cur.fetchone()[0]
            print(f"  {t}: {cnt}件")
            # 最新10件
            try:
                cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 10")
                cols = [d[0] for d in cur.description]
                print(f"  カラム: {cols}")
                for row in cur.fetchall():
                    print(f"    {dict(zip(cols, row))}")
            except Exception as e:
                print(f"  取得エラー: {e}")
        conn.close()
    except Exception as e:
        print(f"  読み取り失敗: {e}")

# jsonl の processed 状況
for jl in glob.glob(str(SES / "matching_v3" / "logs" / "*.jsonl")):
    sz = os.path.getsize(jl)
    print(f"\n■ {os.path.basename(jl)} ({sz}b)")
    if sz > 0:
        with open(jl, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        print(f"  総行数: {len(lines)}")
        for l in lines[-5:]:
            try:
                d = json.loads(l)
                print(f"  {d.get('case_id', '?')[:8]} status={d.get('status', '?')} {d.get('case_name', '')[:30]}")
            except:
                print(f"  {l[:80]}")
