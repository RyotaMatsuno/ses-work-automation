import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# line_bridge.pyでPHメッセージをどう処理しているか確認
with open("line_webhook/line_bridge.py", "rb") as f:
    raw = f.read()

content = raw.decode("cp932", errors="replace")

# PH処理ロジックを探す
import re

for kw in ["PH", "最寄り", "station", "engineer_query", "handle_ph", "on_demand", "マッチング"]:
    idx = content.find(kw)
    if idx != -1:
        print(f"=== [{kw}] at {idx} ===")
        print(content[max(0, idx - 100) : idx + 400])
        print()
        break

# ファイル全体の関数一覧
funcs = re.findall(r"^def (\w+)", content, re.MULTILINE)
print("=== 関数一覧 ===")
for f in funcs:
    print(f"  {f}")
