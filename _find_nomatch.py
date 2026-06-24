import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("matching_v3/matching_v3.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

# 「マッチ案件なし」の文字列を全文検索
idx = 0
while True:
    idx = content.find("マッチ案件なし", idx)
    if idx == -1:
        break
    print(f"=== at {idx} ===")
    print(content[max(0, idx - 300) : idx + 300])
    print()
    idx += 1

# 見つからなければ「No match」「案件なし」も
for kw in ["no_match", "case_result", "no_case", "0件", "empty", "send_no"]:
    idx = content.lower().find(kw.lower())
    if idx != -1:
        print(f"=== [{kw}] at {idx} ===")
        print(content[max(0, idx - 200) : idx + 400])
        print()
