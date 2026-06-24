import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t = open("freee/_v3dry.txt", encoding="utf-8", errors="replace").read()
lines = t.splitlines()
print("件名「5月分請求書」の数:", t.count('"subject": "5月分請求書"'))
print("withholding true 行:", t.count('"withholding": true'))
print("withholding false 行:", t.count('"withholding": false'))
print("payment_date:", re.findall(r'"payment_date": "([^"]+)"', t))
print("partner_id:", re.findall(r'"partner_id": (\d+)', t))
print("--- description（明細名） ---")
for d in re.findall(r'"description": "([^"]+)"', t):
    print("   ", d)
print("--- 結果行 ---")
for l in lines:
    if ("完了" in l) or l.strip().startswith(("OK", "SKIP", "NG")):
        print("   ", l.strip())
