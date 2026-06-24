import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.getcwd())
import sheets_reader as SR

ss = SR._open()
data = ss.worksheet("TERRA").get_all_values()

print("=== ヘッダー行(1-4) 列インデックス付き ===")
for r in range(min(4, len(data))):
    for i, v in enumerate(data[r]):
        if v.strip():
            print(f"  row{r} col{i}: {v.strip()}")
    print("  ---")

print("=== 各プロパー/BPの 列9以降の値（請求額列を探す） ===")
for row in data[4:]:
    name = row[3].strip() if len(row) > 3 else ""
    if not name or name in ("氏名", "稼働中合計"):
        continue
    kubun = row[1].strip() if len(row) > 1 else ""
    extra = []
    for i in range(9, min(len(row), 22)):
        v = row[i].strip()
        if v:
            extra.append(f"{i}:{v}")
    print(f"  {name:<10}(区分{kubun}) | " + " ".join(extra))
