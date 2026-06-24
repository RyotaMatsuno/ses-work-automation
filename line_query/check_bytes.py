path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"

with open(path, "rb") as f:
    raw = f.read()

# cp932でエンコードされた日本語プロパティ名のバイト列を探して置換
# 正しいcp932表現（ファイル内に存在するはず）

# cp932バイト列で置換ターゲットを作成
targets = {
    "最寄り駅": "最寄り駅",
    "備考（LINEメモ）": "備考（LINEメモ）",
    "名前": "名前",
    "スキル": "スキル",
    "稼働状況": "稼働状況",
    "稼働可能日": "稼働可能日",
    "担当者": "担当者",
    "所属会社": "所属会社",
    "単価（万円）": "単価（万円）",
    "必要スキル": "必要スキル",
    "尚可スキル": "尚可スキル",
    "案件詳細": "案件詳細",
    "勤務地": "勤務地",
    "リモート": "リモート",
    "期間": "期間",
    "面談希望": "面談希望",
    "案件名": "案件名",
    "ステータス": "ステータス",
    "開始日": "開始日",
    "イニシャル": "イニシャル",
}

# 各ターゲットがcp932でraw内に存在するか確認
found = []
not_found = []
for key in targets:
    b = key.encode("cp932", errors="replace")
    if b in raw:
        found.append(key)
    else:
        not_found.append(f"{key} (bytes: {b.hex()})")

print(f"Found in file ({len(found)}):", found[:5])
print(f"NOT found ({len(not_found)}):", not_found[:5])

# rawをcp932デコードして問題箇所を確認
content_cp932 = raw.decode("cp932", errors="replace")
# _match_stationの箇所を抽出
start = content_cp932.find("def _match_station")
end = content_cp932.find("\ndef ", start + 1)
block = content_cp932[start:end]
# UTF-8でファイルに書き出して確認
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\block_check.txt", "w", encoding="utf-8") as f:
    f.write(block)
print("\nBlock written to block_check.txt")
