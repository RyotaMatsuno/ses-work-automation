import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import os

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for mod in list(sys.modules.keys()):
    if "line_query" in mod:
        del sys.modules[mod]

from line_query import classify_query, handle_line_query

print("=== 最終テスト（APIなし部分） ===")

# 全classify_queryテスト
cases = [
    ("HS 北小金", "HS", "北小金", "標準"),
    ("H.S 北小金", "HS", "北小金", "ドット付き"),
    ("H.S　北小金", "HS", "北小金", "全角スペース"),
    ("hs 北小金", "HS", "北小金", "小文字"),
    ("HS/北小金", "HS", "北小金", "スラッシュ"),
    ("TK 渋谷", "TK", "渋谷", "TK渋谷"),
    ("OA 森林公園", "OA", "森林公園", "OA森林公園"),
]

all_ok = True
for text, exp_ini, exp_sta, desc in cases:
    qtype, params = classify_query(text)
    ok = qtype == "engineer" and params.get("initial") == exp_ini and params.get("station") == exp_sta
    if not ok:
        all_ok = False
    icon = "✅" if ok else "❌"
    print(f"{icon} [{desc}] 「{text}」 → initial={params.get('initial', '?')} station={params.get('station', '?')}")

print()
print("=== handle_line_queryのガード確認 ===")
# 100文字ガードのテスト（APIなし版）
long_texts = [
    ("HS 北小金", False, "クエリ(6文字)"),
    ("H.S 北小金", False, "クエリ(7文字)"),
    (
        "Web系のJAVA案件ありましたらお願いします！長期案件リモート希望の通いは1時間程度まで大丈夫です",
        False,
        "101文字境界テスト",
    ),
]

# 実際の文字数確認
for text, _, desc in long_texts:
    print(f"  [{desc}] 文字数: {len(text.strip())}")

# 送信されたスキルシートの実際の文字数
skillsheet = """おつかれさまです!
現在、5月から阿部氏の案件でお世話になっていた
うちの社員の林が、案件的に元々スポットの可能性もあるってことで
入ってまして、7月から後続案件があって、受注しているけど
開始時期が6月2週目に入らないと分からないって言われたので
今日からまた営業再開することになりました、、、
Web系のJAVA案件ありましたらお願いします!
長期案件、リモート併用希望です。
通いは1時間程度まで大丈夫です。
※リモートもあれば嬉しいけど、常駐も全然相談ください。
よろしくお願いします!
------------------------------
【名 前】H.S(55歳/男性)※業界経験26年"""
print(f"  実際のスキルシートテキスト: {len(skillsheet.strip())}文字 → 100文字超={len(skillsheet.strip()) > 100}")

# handle_line_queryがNoneを返すか確認
result = handle_line_query(skillsheet)
print(f"  handle_line_query(skillsheet) → {'None ✅' if result is None else f'返答あり ❌: {str(result)[:50]}'}")

print()
print(f"総合判定: {'✅ OK' if all_ok else '❌ 要確認'}")
