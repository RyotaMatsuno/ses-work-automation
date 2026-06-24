import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ses_work = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# processed_ids.json の中身確認
p = ses_work / "mail_pipeline" / "processed_ids.json"
with open(p, encoding="utf-8") as f:
    data = json.load(f)

print(f"型: {type(data)}")
if isinstance(data, list):
    print(f"件数: {len(data)}")
    print("先頭5件:", data[:5])
elif isinstance(data, dict):
    print(f"キー数: {len(data)}")
    keys = list(data.keys())
    print("先頭5キー:", keys[:5])
    print("先頭5値:", [data[k] for k in keys[:5]])

# mail_pipeline.py の processed_ids 読み込み部分を抽出
mp = ses_work / "mail_pipeline" / "mail_pipeline.py"
with open(mp, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

print("\n--- processed_ids 関連コード ---")
for i, l in enumerate(lines):
    if "processed_id" in l.lower() or "processed_ids" in l.lower():
        print(f"L{i + 1}: {l.rstrip()}")
