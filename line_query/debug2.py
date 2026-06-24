path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

# UTF-8で読んで_match_stationの文字列を確認
with open(path, encoding="utf-8") as f:
    content = f.read()

start = content.find("def _match_station")
end = content.find("\ndef ", start + 1)
block = content[start:end]
print("=== _match_station current ===")
print(block)
print()

# _text_propの引数に渡している文字列を確認
import re

hits = re.findall(r'_text_prop\(engineer,\s*"([^"]+)"', block)
print("_text_prop keys:", hits)
