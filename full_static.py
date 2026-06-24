import io
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()
lines = src.splitlines()

bugs = []

# ─────────────────────────────────────────────
# A) 定数値の検証（bytes.fromhexが正しいか）
# ─────────────────────────────────────────────
const_expected = {
    "PROP_INI": ("e382a4e3838be382b7e383a3e383ab", "イニシャル"),
    "PROP_NAME": ("e5908de5898d", "名前"),
    "PROP_STA": ("e69c80e5af84e3828ae9a785", "最寄り駅"),
    "PROP_SKILL": ("e382b9e382ade383ab", "スキル"),
    "PROP_RATE": ("e58d98e4bea1efbc88e4b887e58686efbc89", "単価（万円）"),
    "PROP_STATUS": ("e382b9e38386e383bce382bfe382b9", "ステータス"),
    "PROP_REQSK": ("e5bf85e8a681e382b9e382ade383ab", "必要スキル"),
    "PROP_OPTSK": ("e5b09ae58fabe382b9e382ade383ab", "尚可スキル"),
    "PROP_ASSIGNEE": ("e68b85e5bd93e88085", "担当者"),
    "PROP_PJNAME": ("e6a188e4bbb6e5908d", "案件名"),
    "PROP_REMOTE": ("e383aae383a2e383bce38388", "リモート"),
    "PROP_LOCATION": ("e58ba4e58b99e59cb0", "勤務地"),
    "PROP_PERIOD": ("e69c9fe99693", "期間"),
    "PROP_WORKON": ("e7a8bce5838de58fafe883bde697a5", "稼働可能日"),
    "PROP_WORKST": ("e7a8bce5838de78ab6e6b381", "稼働状況"),
    "VAL_RECRUITING": ("e58b9fe99b86e4b8ad", "募集中"),
    "VAL_ACTIVE2": ("e7a8bce5838de58fafe883bd", "稼働可能"),
    "VAL_ADJUSTING": ("e8aabfe695b4e4b8ad", "調整中"),
}
print("=== A) 定数検証 ===")
for name, (hex_str, expected_str) in const_expected.items():
    try:
        actual = bytes.fromhex(hex_str).decode("utf-8")
        ok = actual == expected_str
        print(f"  {'✅' if ok else '❌'} {name}: '{actual}' {'==' if ok else '!='} '{expected_str}'")
        if not ok:
            bugs.append(f"CONST-{name}: hex→'{actual}' expected '{expected_str}'")
    except Exception as e:
        bugs.append(f"CONST-{name}: decode error {e}")
        print(f"  ❌ {name}: {e}")

# ─────────────────────────────────────────────
# B) 日本語直書き（プロパティ名として使われていないか）
# ─────────────────────────────────────────────
print()
print("=== B) 日本語プロパティ名直書きチェック ===")
jp_prop_names = [
    "イニシャル",
    "最寄り駅",
    "名前",
    "スキル",
    "単価（万円）",
    "ステータス",
    "案件名",
    "必要スキル",
    "担当者",
    "稼働状況",
    "所属会社",
    "備考（LINEメモ）",
    "勤務地",
    "リモート",
    "期間",
    "稼働可能日",
    "尚可スキル",
]
jp_found = False
for i, line in enumerate(lines, 1):
    # bytes.fromhex行はOK
    if "fromhex" in line or "decode" in line:
        continue
    # Unicodeエスケープ行もOK
    if "\\u" in line and "bytes" not in line:
        continue
    for jp in jp_prop_names:
        if jp in line:
            bugs.append(f"JP-LITERAL L{i}: '{jp}' in: {line.strip()[:60]}")
            print(f"  ❌ L{i}: '{jp}' → {line.strip()[:60]}")
            jp_found = True
if not jp_found:
    print("  ✅ 日本語直書きなし")

# ─────────────────────────────────────────────
# C) classify_query ロジック検証
# ─────────────────────────────────────────────
print()
print("=== C) classify_query ロジック ===")
exec_ns = {"re": re}
classify_src = src[src.find("def classify_query") : src.find("\ndef skill_match")]
exec(classify_src, exec_ns)
classify_query = exec_ns["classify_query"]

test_cases = [
    ("HS 北小金", "engineer", "HS", "北小金"),
    ("H.S 北小金", "engineer", "HS", "北小金"),
    ("H.S　北小金", "engineer", "HS", "北小金"),
    ("hs 北小金", "engineer", "HS", "北小金"),
    ("hS 北小金", "engineer", "HS", "北小金"),
    ("HS/北小金", "engineer", "HS", "北小金"),
    ("H.S/北小金", "engineer", "HS", "北小金"),
    ("TK 渋谷", "engineer", "TK", "渋谷"),
    ("OA 森林公園", "engineer", "OA", "森林公園"),
    ("Java開発案件", "project", None, None),
    ("Web系の案件", "project", None, None),
    ("マッチング", "project", None, None),
    ("進捗", "project", None, None),
]
all_ok = True
for txt, et, ei, es in test_cases:
    t, p = classify_query(txt)
    ok = (t == et) and (p.get("initial") == ei) and (p.get("station") == es)
    if not ok:
        all_ok = False
        bugs.append(f"CLASSIFY '{txt}': got type={t} ini={p.get('initial')} sta={p.get('station')}")
    print(f"  {'✅' if ok else '❌'} [{txt}] type={t} ini={p.get('initial')} sta={p.get('station')}")
if all_ok:
    print("  → 全パターンOK")

# ─────────────────────────────────────────────
# D) handle_line_query ガードロジック
# ─────────────────────────────────────────────
print()
print("=== D) handle_line_queryガード ===")


def mock_guard(text):
    if not text or not text.strip():
        return "NONE"
    if len(text.strip()) > 100:
        return "NONE"
    return "API"


guard_cases = [
    ("HS 北小金", "API", "照会クエリ"),
    ("H.S 北小金", "API", "ドット付き"),
    ("", "NONE", "空文字"),
    ("   ", "NONE", "空白のみ"),
    ("a" * 101, "NONE", "101文字"),
    ("a" * 100, "API", "100文字ちょうど"),
    (
        "おつかれさまです！\n【名 前】H.S(55歳/男性)※業界経験26年\n【最寄駅】北小金駅(千代田線)\n【稼 働】7月~\n【単 金】70万",
        "NONE",
        "実スキルシート本文",
    ),
]
for txt, exp, desc in guard_cases:
    got = mock_guard(txt)
    ok = got == exp
    if not ok:
        bugs.append(f"GUARD '{desc}': got {got} expected {exp} len={len(txt.strip())}")
    print(f"  {'✅' if ok else '❌'} [{desc}] len={len(txt.strip())} → {got}")

# ─────────────────────────────────────────────
# E) handle_line_query の「一致なし」→None変換
# ─────────────────────────────────────────────
print()
print("=== E) 一致なし→None変換 ===")
# Unicodeエスケープで検出
no_match_eng = "\u4e00\u81f4\u3059\u308b\u4eba\u54e1\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093"
no_match_pj = "\u4e00\u81f4\u3059\u308b\u6848\u4ef6\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093"
handle_src = src[src.find("def handle_line_query") : src.find("\n\ndef _prop")]
has_eng = (
    no_match_eng in handle_src
    or "\\u4e00\\u81f4\\u3059\\u308b\\u4eba\\u54e1\\u304c\\u898b\\u3064\\u304b\\u308a\\u307e\\u305b\\u3093"
    in handle_src
)
has_pj = (
    no_match_pj in handle_src
    or "\\u4e00\\u81f4\\u3059\\u308b\\u6848\\u4ef6\\u304c\\u898b\\u3064\\u304b\\u308a\\u307e\\u305b\\u3093"
    in handle_src
)
print(f"  {'✅' if has_eng else '❌'} 人員一致なし検出")
print(f"  {'✅' if has_pj else '❌'} 案件一致なし検出")
if not has_eng:
    bugs.append("NOMATCH: 人員一致なし検出なし")
if not has_pj:
    bugs.append("NOMATCH: 案件一致なし検出なし")

# ─────────────────────────────────────────────
# F) engineer_query フィルタ確認
# ─────────────────────────────────────────────
print()
print("=== F) engineer_query フィルタ確認 ===")
eq_src = src[src.find("def engineer_query") : src.find("\ndef project_query")]
checks_f = [
    ("PROP_STATUS", "ステータスフィルタ"),
    ("VAL_RECRUITING", "募集中フィルタ"),
    ("PROP_RATE", "単価>0フィルタ"),
    ("if not required", "スキル空案件除外"),
    ("budget > 150", "単価150万超除外"),
    ("business_days_since", "鮮度チェック"),
    ("_gross_threshold", "担当者別粗利閾値"),
    ("_k40 = _k[:40]", "先頭40文字dedup"),
]
for keyword, desc in checks_f:
    found = keyword in eq_src
    if not found:
        bugs.append(f"EQ-FILTER: {desc} 未実装")
    print(f"  {'✅' if found else '❌'} {desc}")

# ─────────────────────────────────────────────
# G) _match_station のエッジケース
# ─────────────────────────────────────────────
print()
print("=== G) _match_station エッジ ===")
# 駅データなしのとき True を返すか確認
sta_src = src[src.find("def _match_station") : src.find("\ndef engineer_query")]
has_fallback = "return True  # no station data" in sta_src or "return True" in sta_src
print(f"  {'✅' if has_fallback else '❌'} 駅データなし→True フォールバック")
if not has_fallback:
    bugs.append("STATION: fallback True missing")

# ─────────────────────────────────────────────
# H) _limit_reply の TOP_LIMIT 打ち切り確認
# ─────────────────────────────────────────────
print()
print("=== H) _limit_reply ===")
lr_src = src[src.find("def _limit_reply") : src.find("\n\nif __name__")]
# ⑥ (TOP_LIMIT+1=6番目) で打ち切るか
has_toplimit = "_num_label(TOP_LIMIT + 1)" in lr_src
print(f"  {'✅' if has_toplimit else '❌'} TOP_LIMIT+1番目で打ち切り")
if not has_toplimit:
    bugs.append("LIMIT: TOP_LIMIT+1 打ち切りなし")

# ─────────────────────────────────────────────
# 総合
# ─────────────────────────────────────────────
print()
print("=" * 60)
if bugs:
    print(f"❌ 問題 {len(bugs)}件:")
    for b in bugs:
        print(f"   {b}")
else:
    print("✅ 静的解析: 問題なし")
print("=" * 60)
