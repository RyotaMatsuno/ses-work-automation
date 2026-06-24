import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 全定数を実際にdecodeして確認
import re

all_ok = True
print("=== 全定数 decode 最終確認 ===")
for m in re.finditer(r'(PROP_\w+|VAL_\w+)\s*=\s*bytes\.fromhex\("([0-9a-f]+)"\)\.decode\(\)', src):
    name, hex_str = m.group(1), m.group(2)
    decoded = bytes.fromhex(hex_str).decode("utf-8")
    # 期待値マップ
    expected = {
        "PROP_INI": "イニシャル",
        "PROP_NAME": "名前",
        "PROP_STA": "最寄り駅",
        "PROP_MEMO": "備考（LINEメモ）",
        "PROP_SKILL": "スキル",
        "PROP_RATE": "単価（万円）",
        "PROP_STATUS": "ステータス",
        "PROP_REQSK": "必要スキル",
        "PROP_OPTSK": "尚可スキル",
        "PROP_ASSIGNEE": "担当者",
        "PROP_PJNAME": "案件名",
        "PROP_PJDETAIL": "案件詳細",
        "PROP_REMOTE": "リモート",
        "PROP_LOCATION": "勤務地",
        "PROP_PERIOD": "期間",
        "PROP_WORKON": "稼働可能日",
        "PROP_WORKST": "稼働状況",
        "PROP_AFFIL": "所属会社",
        "VAL_RECRUITING": "募集中",
        "VAL_ACTIVE1": "稼働中",
        "VAL_ACTIVE2": "稼働可能",
        "VAL_ADJUSTING": "調整中",
    }
    exp = expected.get(name, "(未登録)")
    ok = (decoded == exp) if exp != "(未登録)" else True
    if not ok:
        all_ok = False
    print(f"  {'✅' if ok else '❌'} {name}: '{decoded}' {'== ' if ok else '!= '}{exp}")

print()
print(f"結果: {'✅ 全定数OK' if all_ok else '❌ 要修正あり'}")
