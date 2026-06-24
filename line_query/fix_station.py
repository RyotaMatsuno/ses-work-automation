import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# 最寄り駅bytes
prop_sta = bytes([0xE6, 0x9C, 0x80, 0xE5, 0xAF, 0x84, 0xE3, 0x82, 0x8A, 0xE9, 0xA7, 0x85])
# 備考（LINEメモ）bytes
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

# 現在の_match_stationブロックを特定してbytesレベルで置換
old_block_marker_start = b"def _match_station"
old_block_marker_end = b"\r\n\r\n\r\n"  # 関数の末尾

idx_start = raw.find(old_block_marker_start)
# engineer_query の直前まで
idx_end = raw.find(b"def engineer_query")

if idx_start == -1 or idx_end == -1:
    print("ERROR: markers not found")
    exit(1)


def b(s):
    return s.encode("ascii")


# 新しい _match_station:
# sta があれば station が含まれるか確認
# memo があれば station が含まれるか確認
# どちらにも station が「見つからない」か「データなし」ならTrueを返す（イニシャル一致を優先）
new_station_func = (
    b("def _match_station(engineer: dict, station: str) -> bool:\r\n")
    + b("    _PROP_STA = '")
    + prop_sta
    + b("'\r\n")
    + b("    _PROP_MEMO = '")
    + prop_memo
    + b("'\r\n")
    + b("    if not station:\r\n")
    + b("        return True\r\n")
    + b("    sta = _text_prop(engineer, _PROP_STA)\r\n")
    + b("    if sta:\r\n")
    + b("        return station in sta\r\n")
    + b("    memo = _text_prop(engineer, _PROP_MEMO)\r\n")
    + b("    if memo and station in memo:\r\n")
    + b("        return True\r\n")
    + b("    return True  # no station data -> match by initial only\r\n")
    + b("\r\n\r\n\r\n")
)

# _match_station 以外の部分（_normalize_initial, _match_initial）はそのまま
# _match_station の開始〜engineer_query 直前を置換
before = raw[:idx_start]
# _match_station の手前（_normalize_initial と _match_initial）
# before に続けて _match_initial の末尾まで取得
# _match_station の開始を正確に切り出す
after = raw[idx_end:]  # engineer_query 以降

# _match_stationより前（_normalize_initial + _match_initial）は保持
middle_start = raw.find(b"def _normalize_initial")
middle_end = raw.find(b"def _match_station")
before_station = raw[middle_start:middle_end]

# ファイル全体を再構成
pre_functions = raw[:middle_start]

new_raw = pre_functions + before_station + new_station_func + after

with open(fpath, "wb") as f:
    f.write(new_raw)

print("Written:", len(new_raw), "bytes")

# 確認
with open(fpath, "rb") as f:
    verify = f.read()

# _match_station が正しく書かれているか
idx = verify.find(b"def _match_station")
chunk = verify[idx : idx + 400]
# bytes として表示（日本語はhex）
print("_match_station block (hex for non-ascii):")
result = ""
for byte in chunk:
    if byte < 128:
        result += chr(byte)
    else:
        result += f"[{byte:02x}]"
print(result)
