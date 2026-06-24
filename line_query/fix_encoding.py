import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# UTF-8でデコード（壊れた箇所はreplaceで読む）
text = raw.decode("utf-8", errors="replace")

# 置換対象の境界
start = text.find("def _normalize_initial")
end = text.find("def engineer_query")

if start == -1 or end == -1:
    print("ERROR: target functions not found")
    exit(1)

print("start:", start, "end:", end)
print("block to replace:")
print(repr(text[start:end]))

# 置換後の3関数を bytes として構築（日本語は直接encode）
new_funcs = (
    "def _normalize_initial(s: str) -> str:\r\n"
    "    import re as _re2\r\n"
    "    return _re2.sub(r'[\\s\\u3000.\\u30fb\\u00b7]', '', s).upper()\r\n"
    "\r\n"
    "\r\n"
    "def _match_initial(engineer: dict, initial: str) -> bool:\r\n"
    "    # "
    + "\u30a4\u30cb\u30b7\u30e3\u30eb"
    + "\u30d5\u30a3\u30fc\u30eb\u30c9\u304c\u3042\u308c\u3070\u305d\u3061\u3089\u3067\u7167\u5408\u3001\u306a\u3051\u308c\u3070\u540d\u524d\u30d5\u30a3\u30fc\u30eb\u30c9\u3067\u30d5\u30a9\u30fc\u30eb\u30d0\u30c3\u30af\r\n"
    "    _PROP_INI = " + "'" + "\u30a4\u30cb\u30b7\u30e3\u30eb" + "'" + "\r\n"
    "    _PROP_NAME = " + "'" + "\u540d\u524d" + "'" + "\r\n"
    "    ini = _text_prop(engineer, _PROP_INI)\r\n"
    "    if ini:\r\n"
    "        return _normalize_initial(ini) == initial.upper()\r\n"
    "    name = _text_prop(engineer, _PROP_NAME)\r\n"
    "    return _normalize_initial(name) == initial.upper()\r\n"
    "\r\n"
    "\r\n"
    "def _match_station(engineer: dict, station: str) -> bool:\r\n"
    "    # "
    + "\u6700\u5bc4\u308a\u99c5\u30d5\u30a3\u30fc\u30eb\u30c9\u307e\u305f\u306f\u5099\u8003\u3067\u7167\u5408\u3001\u30c7\u30fc\u30bf\u306a\u3051\u308c\u3070True\r\n"
    "    _PROP_STA = " + "'" + "\u6700\u5bc4\u308a\u99c5" + "'" + "\r\n"
    "    _PROP_MEMO = " + "'" + "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09" + "'" + "\r\n"
    "    sta = _text_prop(engineer, _PROP_STA)\r\n"
    "    if sta:\r\n"
    "        return station in sta\r\n"
    "    memo = _text_prop(engineer, _PROP_MEMO)\r\n"
    "    if memo:\r\n"
    "        return station in memo\r\n"
    "    return True\r\n"
    "\r\n"
    "\r\n"
    "\r\n"
)

# バイトに変換
new_funcs_bytes = new_funcs.encode("utf-8")

# 元テキストをbytesで組み立て
before_bytes = text[:start].encode("utf-8")
after_bytes = text[end:].encode("utf-8")

new_raw = before_bytes + new_funcs_bytes + after_bytes

with open(fpath, "wb") as f:
    f.write(new_raw)

print("Written:", len(new_raw), "bytes")
print("Verifying...")

# 確認
with open(fpath, "rb") as f:
    verify = f.read().decode("utf-8", errors="replace")

idx = verify.find("def _match_initial")
print("_match_initial snippet:")
print(repr(verify[idx : idx + 300]))
