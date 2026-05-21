
import sys, json
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
from sheets_reader import load_active_entries

entries = load_active_entries()
# FTだけ表示
ft = [e for e in entries if e["source"] == "FT"]
result = [{"name": e["name"], "profit": e["profit"], "seikyu": e["seikyu"], "rule": e["rule"]} for e in ft]
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\ft_check.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"FT {len(ft)}名")
