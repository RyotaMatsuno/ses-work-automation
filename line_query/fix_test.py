import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8", errors="replace")

# 置換対象: _normalize_initial から engineer_query の直前まで
start = text.find("def _normalize_initial")
end = text.find("def engineer_query")

if start == -1 or end == -1:
    print("ERROR: target functions not found")
    exit(1)

old_block = text[start:end]

# 正しい3関数（日本語文字列を直接UTF-8で記述）
new_block = (
    "def _normalize_initial(s: str) -> str:\n"
    "    import re as _re2\n"
    "    return _re2.sub(r'[\\s\\u3000.\\u30fb\\u00b7]', '', s).upper()\n"
    "\n"
    "\n"
    "def _match_initial(engineer: dict, initial: str) -> bool:\n"
    "    ini = _text_prop(engineer, \u30a4\u30cb\u30b7\u30e3\u30eb_KEY)\n"
    "    if ini:\n"
    "        return _normalize_initial(ini) == initial.upper()\n"
    "    name = _text_prop(engineer, \u540d\u524d_KEY)\n"
    "    return _normalize_initial(name) == initial.upper()\n"
    "\n"
    "\n"
    "def _match_station(engineer: dict, station: str) -> bool:\n"
    "    sta = _text_prop(engineer, \u6700\u5bc4\u308a\u99c5_KEY)\n"
    "    if sta:\n"
    "        return station in sta\n"
    "    memo = _text_prop(engineer, \u5099\u8003_KEY)\n"
    "    if memo:\n"
    "        return station in memo\n"
    "    return True  # データなし -> イニシャルのみでマッチ\n"
    "\n"
    "\n"
    "\n"
)

print("ERROR: This approach has issues - using direct string write instead")
