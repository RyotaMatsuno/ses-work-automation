import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# 現在の format_project_result の先頭2行のバイト列を特定
# def format_project_result(engineer: dict, projects: list) -> str:
#     initial = _text_prop(engineer, "化けた文字")
#     station = _text_prop(engineer, "化けた文字")
# を正しいキーで置き換える

# バイト列で検索・置換

# 旧: initial = _text_prop(engineer, "イニシャル[化け]")
# 新: initial = _text_prop(engineer, "イニシャル") or _text_prop(engineer, "名前")

# ASCII部分でマーカーを探す
marker = b"def format_project_result"
idx = raw.find(marker)
if idx == -1:
    print("ERROR: format_project_result not found")
    exit(1)

# その後の "initial = _text_prop" 行を探す
line_start = raw.find(b"    initial = _text_prop", idx)
line_end = raw.find(b"\r\n", line_start) + 2

print("old initial line:", raw[line_start:line_end])
print("hex:", raw[line_start:line_end].hex())

# 次の station 行
line2_start = raw.find(b"    station = _text_prop", line_end)
line2_end = raw.find(b"\r\n", line2_start) + 2

print("old station line:", raw[line2_start:line2_end])
print("hex:", raw[line2_start:line2_end].hex())

# イニシャル bytes: e382a4 e3838b e382b7 e383a3 e383ab
prop_ini = bytes([0xE3, 0x82, 0xA4, 0xE3, 0x83, 0x8B, 0xE3, 0x82, 0xB7, 0xE3, 0x83, 0xA3, 0xE3, 0x83, 0xAB])
# 名前 bytes: e5908d e5898d
prop_name = bytes([0xE5, 0x90, 0x8D, 0xE5, 0x89, 0x8D])
# 最寄り駅 bytes: e69c80 e5af84 e3828a e9a785
prop_sta = bytes([0xE6, 0x9C, 0x80, 0xE5, 0xAF, 0x84, 0xE3, 0x82, 0x8A, 0xE9, 0xA7, 0x85])

new_initial_line = (
    b"    initial = _text_prop(engineer, '" + prop_ini + b"') or _text_prop(engineer, '" + prop_name + b"')\r\n"
)
new_station_line = b"    station = _text_prop(engineer, '" + prop_sta + b"')\r\n"

new_raw = raw[:line_start] + new_initial_line + raw[line_end:line2_start] + new_station_line + raw[line2_end:]

with open(fpath, "wb") as f:
    f.write(new_raw)

print("Written OK")

# 確認
with open(fpath, "rb") as f:
    verify = f.read()
idx2 = verify.find(b"def format_project_result")
chunk = verify[idx2 : idx2 + 300]
result = ""
for byte in chunk:
    if byte < 128:
        result += chr(byte)
    else:
        result += f"[{byte:02x}]"
print(result)
