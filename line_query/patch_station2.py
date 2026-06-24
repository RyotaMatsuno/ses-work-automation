path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

# 壊れた_match_stationを丸ごと正しいものに置き換え
# 現状: staを取得してすぐreturn True（条件なし）
# 正: sta/memoにstationが含まれればTrue、どちらにもなければTrue（データなし扱い）

old = '''def _match_station(engineer: dict, station: str) -> bool:
    """最寄り駅フィールド優先、空なら備考（LINEメモ）も検索。
    どちらにも見つからない場合はTrueを返す（イニシャルのみでマッチ）"""
    sta = _text_prop(engineer, "最寄り駅")
    # DBに最寄り駅データなし → イニシャルだけでヒット扱い
    return True'''

new = '''def _match_station(engineer: dict, station: str) -> bool:
    """最寄り駅フィールド優先、空なら備考（LINEメモ）も検索。
    どちらにも見つからない場合はTrueを返す（イニシャルのみでマッチ）"""
    sta = _text_prop(engineer, "最寄り駅")
    if sta:
        return station in sta
    memo = _text_prop(engineer, "備考（LINEメモ）")
    if memo:
        return station in memo
    # DBに最寄り駅データなし → イニシャルだけでヒット扱い
    return True'''

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK")
else:
    # 現状の_match_stationを直接確認
    start = content.find("def _match_station")
    end = content.find("\ndef ", start + 1)
    print("CURRENT:")
    print(repr(content[start:end]))
