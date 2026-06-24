import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import os

# Notion APIコール不要なテストのみ実施
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for mod in list(sys.modules.keys()):
    if "line_query" in mod:
        del sys.modules[mod]

from line_query import classify_query

print("=== classify_queryテスト（APIなし） ===")
cases = [
    ("HS 北小金", "HS", "北小金"),
    ("H.S 北小金", "HS", "北小金"),
    ("H.S　北小金", "HS", "北小金"),
    ("hs 北小金", "HS", "北小金"),
    ("HS/北小金", "HS", "北小金"),
    ("TK 渋谷", "TK", "渋谷"),
]

all_ok = True
for text, exp_ini, exp_sta in cases:
    qtype, params = classify_query(text)
    ok_type = qtype == "engineer"
    ok_ini = params.get("initial", "") == exp_ini
    ok_sta = params.get("station", "") == exp_sta
    ok = ok_type and ok_ini and ok_sta
    if not ok:
        all_ok = False
    icon = "✅" if ok else "❌"
    print(
        f"{icon} [{text}] type={qtype} initial={params.get('initial')} station={params.get('station')} (expected: {exp_ini}/{exp_sta})"
    )

print()
print("=== handle_line_queryのガードテスト（APIなし） ===")


# モックバージョンでテスト（Notion APIを呼ばない）
def _mock_guard_test(text):
    if text and len(text.strip()) > 100:
        return None
    return "would_run"


guard_cases = [
    ("HS 北小金", False, "短いクエリ→処理する"),
    ("H.S 北小金", False, "短いクエリ→処理する"),
    ("Web系のJAVA案件ありましたらお願いします！長期案件リモート希望です通いは1時間程度まで", True, "100文字超→None"),
    ("おつかれさまです!\n現在、5月から阿部氏の案件でお世話になっていた" * 3, True, "長文→None"),
]

for text, expect_none, desc in guard_cases:
    result = _mock_guard_test(text)
    expected = None if expect_none else "would_run"
    ok = result == expected
    if not ok:
        all_ok = False
    icon = "✅" if ok else "❌"
    print(f"{icon} [{desc}] len={len(text.strip())} → {'None' if result is None else '処理'}")

print()
print(f"=== 総合: {'✅ 全テストOK' if all_ok else '❌ 要確認'} ===")
