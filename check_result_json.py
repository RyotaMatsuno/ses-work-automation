import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

result = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v2\result.json")
print(f"result.json存在: {result.exists()}")
if result.exists():
    data = json.loads(result.read_text(encoding="utf-8"))
    print(f"件数: {len(data)}")
    if data:
        p = data[0]
        print(f"キー: {list(p.keys())}")
        print(
            f"先頭案件: {p.get('project_name')} / budget={p.get('budget')} / candidates={len(p.get('candidates', []))}"
        )
        if p.get("candidates"):
            c = p["candidates"][0]
            print(f"  候補者キー: {list(c.keys())}")
            print(f"  required: {c.get('required')}")
