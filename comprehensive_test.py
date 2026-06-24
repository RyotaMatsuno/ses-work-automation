import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]

from line_query import PROP_INI, PROP_NAME, PROP_STA, _match_initial, _match_station, classify_query, handle_line_query

print("=" * 70)
print("SUITE-1: classify_query パターン網羅テスト")
print("=" * 70)

cases = [
    # (input, expected_type, expected_initial, expected_station)
    ("HS 北小金", "engineer", "HS", "北小金"),
    ("H.S 北小金", "engineer", "HS", "北小金"),
    ("H.S　北小金", "engineer", "HS", "北小金"),  # 全角スペース
    ("hs 北小金", "engineer", "HS", "北小金"),  # 小文字
    ("hS 北小金", "engineer", "HS", "北小金"),  # 混在
    ("HS/北小金", "engineer", "HS", "北小金"),
    ("TK 渋谷", "engineer", "TK", "渋谷"),
    ("OA 森林公園", "engineer", "OA", "森林公園"),
    ("ABCD 大宮", "engineer", "ABCD", "大宮"),
    ("Java開発", "project", None, None),
    ("Web系の案件", "project", None, None),
    # 100文字超 → handle_line_query で None 返す（classify_queryでなくguardで止まる）
]

all_ok = True
for text, exp_type, exp_ini, exp_sta in cases:
    qtype, params = classify_query(text)
    ok_type = qtype == exp_type
    if exp_type == "engineer":
        ok_ini = params.get("initial") == exp_ini
        ok_sta = params.get("station") == exp_sta
        ok = ok_type and ok_ini and ok_sta
        detail = f"initial={params.get('initial')} station={params.get('station')}"
    else:
        ok = ok_type
        detail = f"name={params.get('name', '')[:20]}"
    if not ok:
        all_ok = False
    print(f"{'✅' if ok else '❌'} [{text[:15]}] → {detail}")

print()
print("=" * 70)
print("SUITE-2: handle_line_query ガードテスト（APIなし）")
print("=" * 70)

guard_cases = [
    ("HS 北小金", False, "短いクエリ"),
    ("H.S 北小金", False, "ドット付き短いクエリ"),
    ("", True, "空文字"),
    ("   ", True, "空白のみ"),
    # 101文字以上
    ("HS " + "北" * 98, True, "101文字超"),
    (
        "おつかれさまです！\nWeb系のJAVA案件ありましたらお願いします！\n【名 前】H.S\n【単 金】70万\nよろしくお願いします",
        True,
        "スキルシート本文",
    ),
]

for text, expect_none, desc in guard_cases:
    result = handle_line_query(text)
    ok = (result is None) == expect_none
    if not ok:
        all_ok = False
    actual = "None" if result is None else f"str({len(result)}文字)"
    print(f"{'✅' if ok else '❌'} [{desc}] len={len(text.strip())} → {actual}")

print()
print("=" * 70)
print("SUITE-3: _match_initial / _match_station 単体テスト")
print("=" * 70)


# H.Sのモックレコード（Notionレコード形式）
def mk_eng(ini="", name="", sta="", memo=""):
    return {
        "properties": {
            PROP_INI: {"type": "rich_text", "rich_text": [{"plain_text": ini}] if ini else []},
            PROP_NAME: {"type": "title", "title": [{"plain_text": name}] if name else []},
            PROP_STA: {"type": "rich_text", "rich_text": [{"plain_text": sta}] if sta else []},
        }
    }


match_cases = [
    # (engineer_mock, query_initial, query_station, expect_match, desc)
    (mk_eng(ini="HS", sta="北小金"), "HS", "北小金", True, "イニシャル+駅名 完全一致"),
    (mk_eng(name="H.S", sta="北小金"), "HS", "北小金", True, "名前H.Sから正規化HS + 駅名"),
    (mk_eng(name="H.S", sta=""), "HS", "北小金", True, "駅なし→True"),
    (mk_eng(name="H.S", sta="北小金"), "TK", "北小金", False, "イニシャル不一致"),
    (mk_eng(ini="TK", sta="渋谷"), "TK", "渋谷", True, "TK渋谷"),
    (mk_eng(ini="OA", sta="森林公園"), "OA", "森林公園", True, "OA森林公園"),
]

for eng, ini, sta, expect, desc in match_cases:
    ok_ini = _match_initial(eng, ini)
    ok_sta = _match_station(eng, sta)
    result = ok_ini and ok_sta
    ok = result == expect
    if not ok:
        all_ok = False
    print(f"{'✅' if ok else '❌'} [{desc}] ini={ok_ini} sta={ok_sta} → {result} (expect:{expect})")

print()
print("=" * 70)
print(f"全テスト結果: {'✅ 全部OK' if all_ok else '❌ 失敗あり'}")
print("=" * 70)
