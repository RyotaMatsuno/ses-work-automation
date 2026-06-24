path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, "rb") as f:
    raw = f.read()

content = raw.decode("utf-8", errors="replace")

# 3502〜4344 を正しい関数で置換
before = content[:3502]
after = content[4344:]

new_funcs = '''def _normalize_initial(s: str) -> str:
    """ドット・スペース・全角スペース・中点を除去して大文字化"""
    import re as _re
    return _re.sub(r'[\\s\u3000.\u30fb\u00b7]', '', s).upper()


def _match_initial(engineer: dict, initial: str) -> bool:
    """イニシャルフィールド優先、空なら名前フィールドで照合"""
    ini = _text_prop(engineer, "イニシャル")
    if ini:
        return _normalize_initial(ini) == initial.upper()
    # フォールバック: 名前フィールド（H.S → HS）
    name = _text_prop(engineer, "名前")
    return _normalize_initial(name) == initial.upper()


def _match_station(engineer: dict, station: str) -> bool:
    """最寄り駅フィールド優先、空なら備考（LINEメモ）も検索。
    どちらにもなければTrueを返す（イニシャルのみでマッチ）"""
    sta = _text_prop(engineer, "最寄り駅")
    if sta:
        return station in sta
    memo = _text_prop(engineer, "備考（LINEメモ）")
    if memo:
        return station in memo
    # DBに最寄り駅データなし → イニシャルだけでヒット扱い
    return True


'''

content_new = before + new_funcs + after

with open(path, "w", encoding="utf-8") as f:
    f.write(content_new)

print(f"Written. New length: {len(content_new)}")

# 確認
with open(path, encoding="utf-8") as f:
    check = f.read()

idx = check.find("def _match_station")
end = check.find("\ndef ", idx + 1)
print("\n=== _match_station (verified) ===")
print(check[idx:end])
