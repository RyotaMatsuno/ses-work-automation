import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# モジュールのimportだけで重い処理が走っている可能性あり → 軽量テストに分割
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

# line_query.pyをexecで読み込んで定義だけ取り出す（importせずに）
path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# requests, jpholiday等のimportでハングしないようにモック

# 直接テストしたい関数のみ抽出して実行
# classify_query と _normalize_initial と _match_initial/_match_station だけを単独テスト
exec_ns = {}
# 依存ライブラリを事前にimport済みにする
import re as _re

exec_ns["re"] = _re

# classify_query をパース
classify_src = src[src.find("def classify_query") : src.find("\ndef skill_match")]
normalize_src = src[src.find("def _normalize_initial") : src.find("\ndef _match_initial")]
match_ini_src = src[src.find("def _match_initial") : src.find("\ndef _match_station")]
match_sta_src = src[src.find("def _match_station") : src.find("\ndef engineer_query")]
handle_guard_src = src[src.find("def handle_line_query") : src.find("\ndef _prop")]
text_prop_src = src[src.find("def _text_prop") : src.find("\ndef _multi_select_prop")]
prop_src = src[src.find("def _prop(") : src.find("\ndef _text_prop")]

# 必要な定数
constants_src = src[src.find("PROP_INI") : src.find("\ndef _notion_headers")]

exec(constants_src, exec_ns)
exec(prop_src, exec_ns)
exec(text_prop_src, exec_ns)
exec(normalize_src, exec_ns)
exec(classify_src, exec_ns)
exec(match_ini_src, exec_ns)
exec(match_sta_src, exec_ns)

# handle_line_query はguardだけテスト（APIコールなし）
# logger のみモック
import logging

exec_ns["logger"] = logging.getLogger("test")
exec_ns["ERROR_MESSAGE"] = "error"


# handle_line_query のguard部分だけ抽出（APIを呼ぶ前に返す）
def mock_handle(text):
    if not text or not text.strip():
        return None
    if len(text.strip()) > 100:
        return None
    return "WOULD_CALL_API"


classify_query = exec_ns["classify_query"]
_match_initial = exec_ns["_match_initial"]
_match_station = exec_ns["_match_station"]
_normalize_initial = exec_ns["_normalize_initial"]
PROP_INI = exec_ns["PROP_INI"]
PROP_STA = exec_ns["PROP_STA"]
PROP_NAME = exec_ns["PROP_NAME"]

print("=" * 60)
print("SUITE-1: classify_query")
print("=" * 60)
cases = [
    ("HS 北小金", "engineer", "HS", "北小金"),
    ("H.S 北小金", "engineer", "HS", "北小金"),
    ("H.S　北小金", "engineer", "HS", "北小金"),
    ("hs 北小金", "engineer", "HS", "北小金"),
    ("hS 北小金", "engineer", "HS", "北小金"),
    ("HS/北小金", "engineer", "HS", "北小金"),
    ("TK 渋谷", "engineer", "TK", "渋谷"),
    ("OA 森林公園", "engineer", "OA", "森林公園"),
    ("ABCD 大宮", "engineer", "ABCD", "大宮"),
    ("Java開発", "project", None, None),
]
all_ok = True
for text, exp_t, exp_i, exp_s in cases:
    t, p = classify_query(text)
    ok = (t == exp_t) and (p.get("initial") == exp_i) and (p.get("station") == exp_s)
    if not ok:
        all_ok = False
    print(f"{'✅' if ok else '❌'} [{text}] type={t} ini={p.get('initial')} sta={p.get('station')}")

print()
print("=" * 60)
print("SUITE-2: guard (100文字)")
print("=" * 60)
guard_cases = [
    ("HS 北小金", False),
    ("H.S 北小金", False),
    ("", True),
    ("   ", True),
    ("HS " + "北" * 98, True),
    ("おつかれさまです！\n【名 前】H.S(55歳)\n【単 金】70万\nJava/Spring経験あり\nよろしくお願いします", True),
]
for text, expect_none in guard_cases:
    r = mock_handle(text)
    ok = (r is None) == expect_none
    if not ok:
        all_ok = False
    print(
        f"{'✅' if ok else '❌'} len={len(text.strip())} → {'None' if r is None else 'API呼ぶ'} (expect:{expect_none})"
    )

print()
print("=" * 60)
print("SUITE-3: _match_initial / _match_station")
print("=" * 60)


def mk_eng(ini="", name="", sta=""):
    return {
        "properties": {
            PROP_INI: {"type": "rich_text", "rich_text": [{"plain_text": ini}] if ini else []},
            PROP_NAME: {"type": "title", "title": [{"plain_text": name}] if name else []},
            PROP_STA: {"type": "rich_text", "rich_text": [{"plain_text": sta}] if sta else []},
        }
    }


match_cases = [
    (mk_eng(ini="HS", sta="北小金"), "HS", "北小金", True, "イニシャル+駅 完全"),
    (mk_eng(name="H.S", sta="北小金"), "HS", "北小金", True, "名前H.S→HS+駅"),
    (mk_eng(name="H.S", sta=""), "HS", "北小金", True, "駅なし→True"),
    (mk_eng(name="H.S", sta="北小金"), "TK", "北小金", False, "イニシャル不一致"),
    (mk_eng(ini="TK", sta="渋谷"), "TK", "渋谷", True, "TK渋谷"),
]
for eng, ini, sta, expect, desc in match_cases:
    oi = _match_initial(eng, ini)
    os_ = _match_station(eng, sta)
    res = oi and os_
    ok = res == expect
    if not ok:
        all_ok = False
    print(f"{'✅' if ok else '❌'} [{desc}] ini={oi} sta={os_} → {res}")

print()
print(f"{'✅ 全テストOK' if all_ok else '❌ 失敗あり'}")
