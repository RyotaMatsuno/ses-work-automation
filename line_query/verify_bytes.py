import os

fpath = os.path.join(os.path.dirname(__file__), "line_query.py")
with open(fpath, "rb") as f:
    raw = f.read()

# _PROP_INI = 'イニシャル' の部分のバイト列を確認
idx = raw.find(b"_PROP_INI = '")
if idx == -1:
    print("_PROP_INI not found")
else:
    chunk = raw[idx : idx + 30]
    print("bytes around _PROP_INI:", chunk.hex())
    # 期待値: e3 82 a4 e3 83 8b e3 82 b7 e3 83 a3 e3 83 ab (イニシャル)
    expected = bytes([0xE3, 0x82, 0xA4, 0xE3, 0x83, 0x8B, 0xE3, 0x82, 0xB7, 0xE3, 0x83, 0xA3, 0xE3, 0x83, 0xAB])
    print("expected hex:", expected.hex())
    if expected in raw:
        print("MATCH: prop_ini bytes found correctly in file")
    else:
        print("NO MATCH: prop_ini bytes NOT found")

# _PROP_STA の確認
idx2 = raw.find(b"_PROP_STA = '")
if idx2 >= 0:
    chunk2 = raw[idx2 : idx2 + 30]
    print("bytes around _PROP_STA:", chunk2.hex())
    expected2 = bytes([0xE6, 0x9C, 0x80, 0xE5, 0xAF, 0x84, 0xE3, 0x82, 0x8A, 0xE9, 0xA7, 0x85])
    if expected2 in raw:
        print("MATCH: prop_sta bytes found correctly in file")
    else:
        print("NO MATCH: prop_sta bytes NOT found")
