path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

# _match_stationのキー文字列のコードポイントを確認
import re

idx = content.find("def _match_station")
end = content.find("\ndef ", idx + 1)
block = content[idx:end]

# _text_prop呼び出しのキーを抽出してコードポイント確認
keys = re.findall(r'_text_prop\(engineer,\s*"([^"]+)"', block)
for k in keys:
    cps = [f"U+{ord(c):04X}" for c in k]
    print(f"key={k!r} codepoints={cps}")
