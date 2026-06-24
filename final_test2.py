import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import os

# 最終テスト（全修正後）
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

# キャッシュクリア
for mod in list(sys.modules.keys()):
    if "line_query" in mod:
        del sys.modules[mod]

from line_query import classify_query, handle_line_query

print("=" * 60)
print("修正後 最終テスト")
print("=" * 60)

test_cases = [
    # (入力, 期待するengineer/project/None, 説明)
    ("HS 北小金", "engineer", "正常: スペース区切り"),
    ("H.S 北小金", "engineer", "修正6: ドット付きイニシャル"),
    ("H.S　北小金", "engineer", "修正6: 全角スペース"),
    ("hs 北小金", "engineer", "小文字"),
    ("HS/北小金", "engineer", "スラッシュ区切り"),
    ("Web系のJAVA案件ありましたらお願い", "None", "修正7: 短い長文→None"),
    (
        "おつかれさまです!\n現在、5月から阿部氏の案件でお世話になっていた\nうちの社員の林が、",
        "None",
        "修正7: 長文→None",
    ),
]

all_ok = True
for text, expected, desc in test_cases:
    short_text = text.replace("\n", " ")[:30]

    qtype, params = classify_query(text.split("\n")[0])  # 1行目だけclassify確認
    result = handle_line_query(text)

    if expected == "None":
        ok = result is None
        actual = "None" if result is None else f"返答あり({len(result)}文字)"
    elif expected == "engineer":
        ok = qtype == "engineer" and result is not None and "マッチ" in result
        actual = f"type={qtype} result={result.split(chr(10))[0] if result else 'None'}"
    else:
        ok = True
        actual = str(result)[:50] if result else "None"

    icon = "✅" if ok else "❌"
    if not ok:
        all_ok = False
    print(f"{icon} [{desc}]")
    print(f"   入力: 「{short_text}」")
    print(f"   期待: {expected} / 実際: {actual}")
    print()

print("=" * 60)
print(f"総合判定: {'✅ 全テストOK' if all_ok else '❌ 要確認あり'}")
print("=" * 60)
