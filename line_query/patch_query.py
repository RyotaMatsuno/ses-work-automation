path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

# engineer_queryのマッチング部分を修正
# 現在: イニシャルフィールドと最寄り駅フィールドのみ照合
# 修正: イニシャルが空なら名前フィールド（ドット・スペース除去）でもマッチ
#       最寄り駅が空なら備考（LINEメモ）も検索対象に

old = """def engineer_query(initial: str, station: str) -> str:
    engineers = fetch_all_pages(ENGINEER_DB_ID)
    matched_engineers = [
        engineer
        for engineer in engineers
        if _contains(_text_prop(engineer, "イニシャル"), initial)
        and _contains(_text_prop(engineer, "最寄り駅"), station)
    ]"""

new = '''def _normalize_initial(s: str) -> str:
    """ドット・スペース・全角スペースを除去して大文字化"""
    return re.sub(r'[\\s\u3000.\u30fb]', '', s).upper()


def _match_initial(engineer: dict, initial: str) -> bool:
    """イニシャルフィールド優先、空なら名前フィールドで照合"""
    ini = _text_prop(engineer, "イニシャル")
    if ini:
        return _normalize_initial(ini) == initial.upper()
    # フォールバック: 名前フィールド（H.S → HS）
    name = _text_prop(engineer, "名前")
    return _normalize_initial(name) == initial.upper()


def _match_station(engineer: dict, station: str) -> bool:
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

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("OK: patched engineer_query")
else:
    # 前後を確認
    idx = content.find("def engineer_query")
    print(f"NOT FOUND at exact match. engineer_query at index: {idx}")
    print(repr(content[idx : idx + 300]))
