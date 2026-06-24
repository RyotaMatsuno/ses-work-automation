import datetime
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "freee")
import freee_invoice_v2 as m

xl = m.EXCEL_PATH
print("Excel path:", xl)
print("Excel exists:", os.path.exists(xl))
if os.path.exists(xl):
    print("Excel mtime:", datetime.datetime.fromtimestamp(os.path.getmtime(xl)).strftime("%Y-%m-%d %H:%M"))
root = os.path.dirname(os.path.dirname(xl))
SID = "1ORBtxtGqLAwv3YU8CGeLX7gWFgvKOivMTCZZiWtYGfI"
hits = []
for dp, dn, fn in os.walk(root):
    if any(s in dp for s in [".git", "node_modules", "__pycache__", ".venv"]):
        continue
    for f in fn:
        if not f.endswith(".py"):
            continue
        p = os.path.join(dp, f)
        try:
            t = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if SID in t or "gspread" in t or "sheets.googleapis" in t or "spreadsheets()" in t:
            tags = []
            if SID in t:
                tags.append("SHEET_ID")
            if "gspread" in t:
                tags.append("gspread")
            if "sheets.googleapis" in t or "spreadsheets()" in t:
                tags.append("sheets_api")
            hits.append((os.path.relpath(p, root), "/".join(tags)))
print("sheet-related scripts:", len(hits))
for h, tg in hits[:40]:
    print("  ", h, "[", tg, "]")
