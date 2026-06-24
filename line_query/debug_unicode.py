path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8", errors="replace") as f:
    content = f.read()

# _match_stationブロックのバイト表現を確認
start = content.find("def _match_station")
end = content.find("\ndef ", start + 1)
block = content[start:end]

# 各文字のコードポイント確認
print("_match_station chars with codepoints:")
for i, ch in enumerate(block):
    if ord(ch) > 127:
        print(f"  [{i}] U+{ord(ch):04X} {repr(ch)}")
