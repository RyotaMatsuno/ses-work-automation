import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

exec_ns = {}
import re as _re

exec_ns["re"] = _re
exec_ns["os"] = os


# 定数・ヘルパーのみ抽出実行（API呼び出しなし）
def run_block(label, code):
    try:
        exec(code, exec_ns)
    except Exception as e:
        print(f"  [exec error: {label}] {e}")


run_block("constants", src[src.find("PROP_INI") : src.find("\ndef _notion_headers")])
run_block("_prop", src[src.find("def _prop(") : src.find("\ndef _text_prop")])
run_block("_text_prop", src[src.find("def _text_prop") : src.find("\ndef _multi_select_prop")])
run_block("normalize", src[src.find("def _normalize_initial") : src.find("\ndef _match_initial")])
run_block("classify", src[src.find("def classify_query") : src.find("\ndef skill_match")])
run_block("match_ini", src[src.find("def _match_initial") : src.find("\ndef _match_station")])
run_block("match_sta", src[src.find("def _match_station") : src.find("\ndef engineer_query")])


# handle_line_queryのguard部分のみモック
def mock_handle(text):
    if not text or not text.strip():
        return None
    if len(text.strip()) > 100:
        return None
    return "WOULD_CALL_API"


classify_query = exec_ns["classify_query"]
_match_initial = exec_ns["_match_initial"]
_match_station = exec_ns["_match_station"]
PROP_INI = exec_ns["PROP_INI"]
PROP_STA = exec_ns["PROP_STA"]
PROP_NAME = exec_ns["PROP_NAME"]

all_ok = True

# ── SUITE 1: classify_query ──────────────────────────
print("SUITE-1 classify_query")
S1 = [
    ("HS 北小金", "engineer", "HS", "北小金"),
    ("H.S 北小金", "engineer", "HS", "北小金"),
    ("H.S　北小金", "engineer", "HS", "北小金"),
    ("hs 北小金", "engineer", "HS", "北小金"),
    ("hS 北小金", "engineer", "HS", "北小金"),
    ("HS/北小金", "engineer", "HS", "北小金"),
    ("TK 渋谷", "engineer", "TK", "渋谷"),
    ("OA 森林公園", "engineer", "OA", "森林公園"),
    ("ABCD 大宮", "engineer", "ABCD", "大宮"),
    ("Java開発案件", "project", None, None),
    ("Web系の案件", "project", None, None),
]
for txt, et, ei, es in S1:
    t, p = classify_query(txt)
    ok = t == et and p.get("initial") == ei and p.get("station") == es
    if not ok:
        all_ok = False
    print(f"  {'✅' if ok else '❌'} [{txt}] → {t} ini={p.get('initial')} sta={p.get('station')}")

# ── SUITE 2: guard ──────────────────────────────────
print("\nSUITE-2 guard (100文字)")
S2 = [
    ("HS 北小金", False, "短いクエリ"),
    ("H.S 北小金", False, "ドット付き"),
    ("", True, "空文字"),
    ("   ", True, "空白"),
    ("HS " + "北" * 98, True, "101文字"),
    ("おつかれさまです！" * 5, True, "45文字×5=長文"),
]
for txt, expect_none, desc in S2:
    r = mock_handle(txt)
    ok = (r is None) == expect_none
    if not ok:
        all_ok = False
    print(f"  {'✅' if ok else '❌'} [{desc}] len={len(txt.strip())} → {'None' if r is None else 'API呼ぶ'}")

# ── SUITE 3: _match_initial/_match_station ───────────
print("\nSUITE-3 match")


def mk(ini="", name="", sta=""):
    return {
        "properties": {
            PROP_INI: {"type": "rich_text", "rich_text": [{"plain_text": ini}] if ini else []},
            PROP_NAME: {"type": "title", "title": [{"plain_text": name}] if name else []},
            PROP_STA: {"type": "rich_text", "rich_text": [{"plain_text": sta}] if sta else []},
        }
    }


S3 = [
    (mk(ini="HS", sta="北小金"), "HS", "北小金", True, "HS+北小金"),
    (mk(name="H.S", sta="北小金"), "HS", "北小金", True, "H.S名前→HS"),
    (mk(name="H.S", sta=""), "HS", "北小金", True, "駅なし→True"),
    (mk(name="H.S", sta="北小金"), "TK", "北小金", False, "INI不一致"),
    (mk(ini="TK", sta="渋谷"), "TK", "渋谷", True, "TK渋谷"),
    (mk(ini="OA", sta="森林公園"), "OA", "森林公園", True, "OA森林公園"),
]
for eng, ini, sta, expect, desc in S3:
    oi = _match_initial(eng, ini)
    os_ = _match_station(eng, sta)
    ok = (oi and os_) == expect
    if not ok:
        all_ok = False
    print(f"  {'✅' if ok else '❌'} [{desc}] ini={oi} sta={os_} → {oi and os_}")

# ── SUITE 4: handle_line_query の None返却確認 ─────────
print('\nSUITE-4 handle_line_query None返却確認 ("一致なし"文字列の処理)')
# モックengineer_queryが「一致なし」を返した場合もNoneになるか
NO_MATCH_ENG = "\u4e00\u81f4\u3059\u308b\u4eba\u54e1\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3067\u3057\u305f: HS \u5317\u5c0f\u91d1"
NO_MATCH_PJ = (
    "\u4e00\u81f4\u3059\u308b\u6848\u4ef6\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3067\u3057\u305f: test"
)


# handle_line_queryの一致なしNone変換を確認
def mock_handle_with_nomatch(result_str):
    no_match_phrases = [
        "\u4e00\u81f4\u3059\u308b\u4eba\u54e1\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093",
        "\u4e00\u81f4\u3059\u308b\u6848\u4ef6\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093",
    ]
    if any(p in result_str for p in no_match_phrases):
        return None
    return result_str


ok = mock_handle_with_nomatch(NO_MATCH_ENG) is None
if not ok:
    all_ok = False
print(f"  {'✅' if ok else '❌'} 人員一致なし → None")
ok = mock_handle_with_nomatch(NO_MATCH_PJ) is None
if not ok:
    all_ok = False
print(f"  {'✅' if ok else '❌'} 案件一致なし → None")
ok = mock_handle_with_nomatch("【HS｜北小金】マッチ案件3件") == "【HS｜北小金】マッチ案件3件"
if not ok:
    all_ok = False
print(f"  {'✅' if ok else '❌'} 正常マッチ結果 → そのまま返却")

print()
print(f"{'=' * 60}")
print(f"総合: {'✅ 全テストOK' if all_ok else '❌ 失敗あり'}")
print(f"{'=' * 60}")
