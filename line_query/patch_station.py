path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

old = '''def _match_station(engineer: dict, station: str) -> bool:
    """最寄り駅フィールド優先、空なら備考（LINEメモ）も検索"""
    sta = _text_prop(engineer, "最寄り駅")
    if sta:
        return station in sta
    # フォールバック: 備考（LINEメモ）に最寄り駅が書かれているケース
    memo = _text_prop(engineer, "備考（LINEメモ）")
    return station in memo


def engineer_query(initial: str, station: str) -> str:
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = [
        engineer
        for engineer in engineers
        if _match_initial(engineer, initial)
        and _match_station(engineer, station)
    ]'''

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
    return True


def engineer_query(initial: str, station: str) -> str:
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = [
        engineer
        for engineer in engineers
        if _match_initial(engineer, initial)
        and _match_station(engineer, station)
    ]'''

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: patched _match_station")
else:
    print("NOT FOUND")
