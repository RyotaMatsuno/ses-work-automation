import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import freee_invoice_monthly as M

dates = M.get_target_dates()
people, _ = M.load_people(dates["target_month"])
groups = M.group_people(people)

key = ("株式会社TERRA", "45")
grp = groups.get(key, [])
props = [p for p in grp if p.get("prop")]
inds = [p for p in grp if not p.get("prop")]

print(f"=== TERRA/45日 プロパー集約 {len(props)}名 ===")
for p in props:
    print(f"  P  {p['name']}  (site={p['site']})")
print(f"=== TERRA/45日 個別行 {len(inds)}名 ===")
for p in inds:
    print(f"  I  {p['name']}  amount={p.get('amount')}")
