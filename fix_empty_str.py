import sys

sys.stdout.reconfigure(encoding="utf-8")

with open("matching_v2/matching_v2.py", encoding="utf-8") as f:
    content = f.read()

old = "    created_at = _parse_iso_datetime(created_at_str)\n    if created_at is None:\n        return False\n"
new = (
    "    if not created_at_str:\n"
    "        return True  # 日付不明は通す\n"
    "    created_at = _parse_iso_datetime(created_at_str)\n"
    "    if created_at is None:\n"
    "        return True  # パース失敗は通す\n"
)

if old in content:
    content = content.replace(old, new, 1)
    with open("matching_v2/matching_v2.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("修正: OK")
else:
    print("対象行が見つかりません")
    # 該当箇所を表示
    for i, line in enumerate(content.split("\n")[250:265], start=251):
        print(f"{i}: {repr(line)}")
