path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

# _text_prop定義を抽出
start = content.find("def _text_prop")
end = content.find("\ndef ", start + 1)
print("=== _text_prop ===")
print(content[start:end])

# _match_initialも確認
start2 = content.find("def _match_initial")
end2 = content.find("\ndef ", start2 + 1)
print("\n=== _match_initial ===")
print(content[start2:end2])
