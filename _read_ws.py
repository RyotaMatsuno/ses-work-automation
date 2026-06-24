import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("line_webhook/webhook_server.py", "rb") as f:
    raw = f.read()
content = raw.decode("cp932", errors="replace")


# "PH" "immediate" "on_demand" "マッチ" 周辺を全抽出
for kw in ["PH?", "immediate", "on_demand", "オンデマンド", "initial_place", "_INITIAL"]:
    idx = content.find(kw)
    if idx != -1:
        print(f"=== [{kw}] at {idx} ===")
        print(content[max(0, idx - 100) : idx + 600])
        print()
