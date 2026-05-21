
import sys, json
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
from sheets_reader import scan_nyujomae, load_active_entries

nyujomae = scan_nyujomae()
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\scan_result.json", "w", encoding="utf-8") as f:
    json.dump(nyujomae, f, ensure_ascii=False, indent=2)

entries = load_active_entries()
summary = [{"source": e["source"], "name": e["name"], "seikyu": e["seikyu"]} for e in entries]
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\active_result.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"入場前: {len(nyujomae)}名, 稼働中: {len(entries)}名")
