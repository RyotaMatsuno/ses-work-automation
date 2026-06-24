path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, "rb") as f:
    raw = f.read()
content = raw.decode("utf-8", errors="replace")

# _normalize_initial, _match_initial, _match_station の3関数を
# Unicodeエスケープ形式（\uXXXX）で書き直す
# これにより文字化けに依存しない

# 各プロパティ名のUnicodeエスケープ
# イニシャル = \u30a4\u30cb\u30b7\u30e3\u30eb
# 名前 = \u540d\u524d
# 最寄り駅 = \u6700\u5bc4\u308a\u99c5
# 備考（LINEメモ） = \u5099\u8003\uff08LINE\u30e1\u30e2\uff09

s = content.find("def _normalize_initial")
e = content.find("\ndef ", content.find("def _match_station") + 1)

before = content[:s]
after = content[e:]

new_code = (
    "def _normalize_initial(s: str) -> str:\n"
    "    import re as _re2\n"
    "    return _re2.sub(r'[\\s\\u3000.\\u30fb\\u00b7]', '', s).upper()\n"
    "\n"
    "\n"
    "def _match_initial(engineer: dict, initial: str) -> bool:\n"
    '    ini = _text_prop(engineer, "\\u30a4\\u30cb\\u30b7\\u30e3\\u30eb")  # イニシャル\n'
    "    if ini:\n"
    "        return _normalize_initial(ini) == initial.upper()\n"
    '    name = _text_prop(engineer, "\\u540d\\u524d")  # 名前\n'
    "    return _normalize_initial(name) == initial.upper()\n"
    "\n"
    "\n"
    "def _match_station(engineer: dict, station: str) -> bool:\n"
    '    sta = _text_prop(engineer, "\\u6700\\u5bc4\\u308a\\u99c5")  # 最寄り駅\n'
    "    if sta:\n"
    "        return station in sta\n"
    '    memo = _text_prop(engineer, "\\u5099\\u8003\\uff08LINE\\u30e1\\u30e2\\uff09")  # 備考（LINEメモ）\n'
    "    if memo:\n"
    "        return station in memo\n"
    "    return True  # データなし → イニシャルのみマッチ\n"
    "\n"
    "\n"
)

content_new = before + new_code + after
with open(path, "w", encoding="utf-8") as f:
    f.write(content_new)
print(f"Written. Length: {len(content_new)}")

# 確認
with open(path, encoding="utf-8") as f:
    check = f.read()
idx = check.find("def _match_station")
end = check.find("\ndef ", idx + 1)
print("\n=== _match_station ===")
print(check[idx:end])
