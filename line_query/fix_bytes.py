import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

text = raw.decode("utf-8", errors="replace")
start = text.find("def _normalize_initial")
end = text.find("def engineer_query")

# 日本語文字列をUnicodeコードポイントから直接bytes生成
# イニシャル = U+30A4 30CB 30B7 30E3 30EB
prop_ini = bytes([0xE3, 0x82, 0xA4, 0xE3, 0x83, 0x8B, 0xE3, 0x82, 0xB7, 0xE3, 0x83, 0xA3, 0xE3, 0x83, 0xAB])
# 名前 = U+540D 524D
prop_name = bytes([0xE5, 0x90, 0x8D, 0xE5, 0x89, 0x8D])
# 最寄り駅 = U+6700 5BC4 308A 99C5
prop_sta = bytes([0xE6, 0x9C, 0x80, 0xE5, 0xAF, 0x84, 0xE3, 0x82, 0x8A, 0xE9, 0xA7, 0x85])
# 備考（LINEメモ） = U+5099 8003 FF08 4C49 4E45 30E1 30E2 FF09
prop_memo = bytes(
    [
        0xE5,
        0x82,
        0x99,
        0xE8,
        0x80,
        0x83,
        0xEF,
        0xBC,
        0x88,
        0x4C,
        0x49,
        0x4E,
        0x45,
        0xE3,
        0x83,
        0xA1,
        0xE3,
        0x83,
        0xA2,
        0xEF,
        0xBC,
        0x89,
    ]
)


# 3関数のソースをbytesで構築（ASCII部分は直接書き、日本語部分はbytes変数を挿入）
def b(s):
    return s.encode("ascii")


new_funcs = (
    b("def _normalize_initial(s: str) -> str:\r\n")
    + b("    import re as _re2\r\n")
    + b(r"    return _re2.sub(r'[\s\u3000.\u30fb\u00b7]', '', s).upper()")
    + b("\r\n")
    + b("\r\n\r\n")
    + b("def _match_initial(engineer: dict, initial: str) -> bool:\r\n")
    + b("    _PROP_INI = '")
    + prop_ini
    + b("'\r\n")
    + b("    _PROP_NAME = '")
    + prop_name
    + b("'\r\n")
    + b("    ini = _text_prop(engineer, _PROP_INI)\r\n")
    + b("    if ini:\r\n")
    + b("        return _normalize_initial(ini) == initial.upper()\r\n")
    + b("    name = _text_prop(engineer, _PROP_NAME)\r\n")
    + b("    return _normalize_initial(name) == initial.upper()\r\n")
    + b("\r\n\r\n")
    + b("def _match_station(engineer: dict, station: str) -> bool:\r\n")
    + b("    _PROP_STA = '")
    + prop_sta
    + b("'\r\n")
    + b("    _PROP_MEMO = '")
    + prop_memo
    + b("'\r\n")
    + b("    sta = _text_prop(engineer, _PROP_STA)\r\n")
    + b("    if sta:\r\n")
    + b("        return station in sta\r\n")
    + b("    memo = _text_prop(engineer, _PROP_MEMO)\r\n")
    + b("    if memo:\r\n")
    + b("        return station in memo\r\n")
    + b("    return True\r\n")
    + b("\r\n\r\n\r\n")
)

before_bytes = text[:start].encode("utf-8")
after_bytes = text[end:].encode("utf-8")
new_raw = before_bytes + new_funcs + after_bytes

with open(fpath, "wb") as f:
    f.write(new_raw)

print("Written:", len(new_raw), "bytes")

# 確認: プロパティ名が正しく書かれているか
with open(fpath, "rb") as f:
    verify_raw = f.read()

verify = verify_raw.decode("utf-8")  # errors指定なし -> 化けていれば例外
print("UTF-8 decode OK")

# _match_initial 部分を表示
idx = verify.find("def _match_initial")
snippet = verify[idx : idx + 350]
print(snippet)
