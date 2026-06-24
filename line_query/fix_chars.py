path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8", errors="replace") as f:
    content = f.read()

# 壊れた文字列 → 正しい文字列
fixes = [
    # 最寄り駅 (寄=\u5bc4, 駅=\u99c5 が壊れている)
    ("最\ufffdり\ufffd", "最寄り駅"),
    # 備考（LINEメモ）
    ("備\ufffd\ufffdLINEメモ\ufffd", "備考（LINEメモ）"),
    # 稼働状況
    ("稼\ufffd状\ufffd", "稼働状況"),
    # 稼働可能日
    ("稼\ufffd可\ufffd日", "稼働可能日"),
    # 担当者
    ("担\ufffd者", "担当者"),
    # 所属会社
    ("所\ufffd会社", "所属会社"),
    # 単価（万円）
    ("単\ufffd（万円）", "単価（万円）"),
    # 必要スキル
    ("必\ufffdスキル", "必要スキル"),
    # 尚可スキル
    ("尚\ufffdスキル", "尚可スキル"),
    # 案件詳細
    ("案\ufffd詳\ufffd", "案件詳細"),
    # 勤務地
    ("勤\ufffd地", "勤務地"),
    # リモート
    ("リモ\ufffd\ufffd", "リモート"),
    # 期間
    ("期\ufffd", "期間"),
    # 面談希望
    ("面\ufffd希\ufffd", "面談希望"),
    # 案件名
    ("案\ufffd名", "案件名"),
    # ステータス
    ("ステ\ufffd\ufffdス", "ステータス"),
    # 開始日
    ("開\ufffd日", "開始日"),
]

count = 0
for bad, good in fixes:
    if bad in content:
        content = content.replace(bad, good)
        count += 1
        print(f"Fixed: {repr(bad)} -> {good}")

print(f"\nTotal fixes: {count}")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Saved.")
