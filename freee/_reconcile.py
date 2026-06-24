import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "freee")  # freee_invoice_v2 (Excel reader)
# sheets_reader は cwd(ses_work) 直下

try:
    import sheets_reader as SR
except Exception as e:
    print("sheets_reader import FAILED:", repr(e))
    raise

import freee_invoice_v2 as XL

print("--- Sheet reader (スプレッドシート) ---")
try:
    s_entries = SR.load_active_entries()
except Exception as e:
    print("Sheet load FAILED:", repr(e))
    raise
print("Sheet count:", len(s_entries))

print("--- Excel reader (ローカル) ---")
x_entries = XL.load_active_entries()
print("Excel count:", len(x_entries))

s_map = {e["name"]: e for e in s_entries}
x_map = {e["name"]: e for e in x_entries}
s_names = set(s_map)
x_names = set(x_map)

print("Sheetのみ(Excelに無い):", sorted(s_names - x_names))
print("Excelのみ(Sheetに無い):", sorted(x_names - s_names))
print("--- 共通で請求額が違う人 ---")
diff = 0
for n in sorted(s_names & x_names):
    if s_map[n].get("seikyu") != x_map[n].get("seikyu"):
        diff += 1
        print(
            f"  {n}: Sheet={s_map[n].get('seikyu'):,} / Excel={x_map[n].get('seikyu'):,} (src={s_map[n].get('source')})"
        )
print("請求額差異人数:", diff)
s_total = sum(e.get("seikyu", 0) for e in s_entries)
x_total = sum(e.get("seikyu", 0) for e in x_entries)
print(f"Sheet合計: {s_total:,} / Excel合計: {x_total:,}")
