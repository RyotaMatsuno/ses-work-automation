path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, "rb") as f:
    raw = f.read()

# UTF-8として読む（エラー箇所は\ufffdに）
content = raw.decode("utf-8", errors="replace")

# 壊れた3関数をまとめて正しいUTF-8で置換
# まず現在の各関数の開始位置を確認
for fname in ["def _normalize_initial", "def _match_initial", "def _match_station"]:
    idx = content.find(fname)
    end = content.find("\ndef ", idx + 1)
    print(f"{fname}: [{idx}:{end}]")
    print(content[idx : idx + 50])
    print()
