import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("=" * 70)
print("STEP-1: 全定数のhex→実際の文字列を検証")
print("=" * 70)

# 全定数を展開して正しいか確認
consts = {
    "PROP_INI": ("e382a4e3838be382b7e383a3e383ab", "イニシャル"),
    "PROP_NAME": ("e5908de5898d", "名前"),
    "PROP_STA": ("e69c80e5af84e3828ae9a785", "最寄り駅"),
    "PROP_MEMO": ("e58299e88083efbc884c494e45e383a1e383a2efbc89", "備考（LINEメモ）"),
    "PROP_SKILL": ("e382b9e382ade383ab", "スキル"),
    "PROP_RATE": ("e58d98e4bea1efbc88e4b887e58686efbc89", "単価（万円）"),
    "PROP_STATUS": ("e382b9e38386e383bce382bfe382b9", "ステータス"),
    "PROP_REQSK": ("e5bf85e8a681e382b9e382ade383ab", "必要スキル"),
    "PROP_OPTSK": ("e5b09ae58fabe382b9e382ade383ab", "尚可スキル"),  # ← 要確認
    "PROP_ASSIGNEE": ("e68b85e5bd93e88085", "担当者"),
    "PROP_PJNAME": ("e6a188e4bbb6e5908d", "案件名"),
    "PROP_PJDETAIL": ("e6a188e4bbb6e8a9b3e7b4b0", "案件詳細"),
    "PROP_REMOTE": ("e383aae383a2e383bce38388", "リモート"),
    "PROP_LOCATION": ("e58ba4e58b99e59cb0", "勤務地"),
    "PROP_PERIOD": ("e69c9fe99693", "期間"),
    "PROP_WORKON": ("e7a8bce5838de58fafe883bde697a5", "稼働可能日"),
    "PROP_WORKST": ("e7a8bce5838de78ab6e6b381", "稼働状況"),
    "PROP_AFFIL": ("e68980e5b19ee4bc9ae7a4be", "所属会社"),
    "VAL_RECRUITING": ("e58b9fe99b86e4b8ad", "募集中"),
    "VAL_ACTIVE1": ("e7a8bce5838de4b8ad", "稼働中"),
    "VAL_ACTIVE2": ("e7a8bce5838de58fafe883bd", "稼働可能"),
    "VAL_ADJUSTING": ("e8aabfe695b4e4b8ad", "調整中"),
}

# 各定数の期待値と実際のhex→文字列を比較
all_ok = True
for name, (hexstr, expected) in consts.items():
    try:
        actual = bytes.fromhex(hexstr).decode("utf-8")
    except Exception as e:
        actual = f"DECODE ERROR: {e}"
    ok = actual == expected
    if not ok:
        all_ok = False
        print(f"  ❌ {name}: hex→'{actual}' (期待:'{expected}')")
    else:
        print(f"  ✅ {name}: '{actual}'")

print()
# 正しいhexを計算して比較
print("=== 不一致のものを正しいhexで再確認 ===")
for name, (hexstr, expected) in consts.items():
    actual = bytes.fromhex(hexstr).decode("utf-8", errors="replace")
    if actual != expected:
        correct_hex = expected.encode("utf-8").hex()
        print(f"  {name}:")
        print(f"    現在のhex: {hexstr}")
        print(f"    正しいhex: {correct_hex}")
        print(f"    現在の値:  '{actual}'")
        print(f"    正しい値:  '{expected}'")
