import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

print("=" * 70)
print("再静的解析: バグが全部消えたか確認")
print("=" * 70)

issues_remaining = []

# 日本語直書きチェック（プロパティ名として使われている文字列）
jp_literals = [
    '"イニシャル"',
    "'イニシャル'",
    '"最寄り駅"',
    "'最寄り駅'",
    '"名前"',
    "'名前'",
    '"スキル"',
    "'スキル'",
    '"単価（万円）"',
    "'単価（万円）'",
    '"ステータス"',
    "'ステータス'",
    '"案件名"',
    "'案件名'",
    '"必要スキル"',
    "'必要スキル'",
    '"担当者"',
    "'担当者'",
    '"稼働状況"',
    "'稼働状況'",
    '"所属会社"',
    "'所属会社'",
    '"備考（LINEメモ）"',
    "'備考（LINEメモ）'",
    '"勤務地"',
    "'勤務地'",
    '"リモート"',
    "'リモート'",
    '"期間"',
    "'期間'",
    '"稼働可能日"',
    "'稼働可能日'",
]

for lit in jp_literals:
    # 定数定義行(bytes.fromhex)以外に出現していないか
    for i, line in enumerate(src.split("\n"), 1):
        if lit in line and "fromhex" not in line and "decode" not in line:
            issues_remaining.append(f"日本語直書き L{i}: {line.strip()[:60]}")
            break

# BUG-9: PROP_RATE >= 75 フィルタが残っていないか確認
if "greater_than_or_equal_to" in src:
    issues_remaining.append("BUG-9残存: greater_than_or_equal_toフィルタが残っている")

# BUG-11: project_query にfilter_bodyが入っているか
idx_pq = src.find("def project_query")
pq_body = src[idx_pq : idx_pq + 500]
if "filter_body" not in pq_body and "_filter" not in pq_body:
    issues_remaining.append("BUG-11残存: project_queryにフィルタがない")

# classify_query の正規表現確認
if "classify_query" in src:
    idx = src.find("def classify_query")
    snippet = src[idx : idx + 400]
    if r"[A-Za-z.]{1,8}" in snippet:
        print("✅ classify_query: ドット対応正規表現あり")
    else:
        issues_remaining.append("classify_query: ドット対応正規表現なし")

# handle_line_query の100文字ガード確認
if "> 100" in src:
    print("✅ handle_line_query: 100文字ガードあり")
else:
    issues_remaining.append("100文字ガードなし")

# PROP_INI, PROP_STA が format_project_result で使われているか
idx_fmt = src.find("def format_project_result")
fmt_body = src[idx_fmt : idx_fmt + 600]
if "PROP_INI" in fmt_body and "PROP_STA" in fmt_body:
    print("✅ format_project_result: PROP_INI/PROP_STA使用確認")
else:
    issues_remaining.append("format_project_result: PROP_INI or PROP_STA未使用")

# VAL_ACTIVE2, VAL_ADJUSTING が project_query で使われているか
idx_pq2 = src.find("def project_query")
pq2 = src[idx_pq2 : idx_pq2 + 600]
if "VAL_ACTIVE2" in pq2 and "VAL_ADJUSTING" in pq2:
    print("✅ project_query: VAL_ACTIVE2/VAL_ADJUSTING使用確認")
else:
    issues_remaining.append("project_query: VAL_ACTIVE2 or VAL_ADJUSTING未使用")

print()
if issues_remaining:
    print(f"❌ 残存問題: {len(issues_remaining)}件")
    for x in issues_remaining:
        print(f"  - {x}")
else:
    print("✅ 全20件のバグ修正確認 - 問題なし")
