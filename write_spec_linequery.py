"""SPEC.md for line_query.py bug fixes"""

spec = """# SPEC: line_query.py バグ修正

## 修正対象ファイル
`ses_work/line_webhook/line_query.py`

## バグ一覧と修正内容

### BUG-1: _limit_reply のヘッダー行数が固定2行（L541）
**現状**
```python
limited = lines[:2]  # ヘッダー2行（タイトル＋所属行）を保持
```
**問題**: ヘッダー（タイトル・連絡先・所属）が3行以上になる場合（所属情報が複数行）、案件①の内容が欠落する。

**修正**: ヘッダー行を番号ラベル（①）が出現するまで動的に保持する。
```python
limited = []
for line in lines:
    limited.append(line)
    if line.startswith(_num_label(1)):
        # ①の行は含めてから案件本文へ
        break
# ①以降のブロックをTOP_LIMIT件まで追加（既存ロジック流用）
for line in lines[len(limited):]:
    if line.startswith(_num_label(TOP_LIMIT + 1)):
        break
    limited.append(line)
```

### BUG-2: _gross_threshold の「共通」担当が3万（L522-523）
**現状**
```python
GROSS_THRESHOLDS = {"松野": 5, "岡本": 3, "共通": 3}
def _gross_threshold(assignee: str) -> int:
    return GROSS_THRESHOLDS.get(assignee, 3)
```
**問題**: 「共通」案件は松野または岡本に割り振られる前の状態。判断マニュアルでは松野=5万・岡本=3万。担当が「共通」または不明の場合は保守的に5万を適用すべき。

**修正**:
```python
GROSS_THRESHOLDS = {"松野": 5, "岡本": 3}
def _gross_threshold(assignee: str) -> int:
    return GROSS_THRESHOLDS.get(assignee, 5)  # 不明・共通は5万
```

### BUG-3: _match_station が駅データなしの場合に True を返す（L174）
**現状**
```python
def _match_station(engineer: dict, station: str) -> bool:
    ...
    return True  # no station data -> match by initial only
```
**問題**: 「HS 北小金」で照会したとき、最寄り駅が未設定のエンジニアも全員マッチする。イニシャルが一致すれば駅が違っても通ってしまう。

**修正**: 
- 駅データあり → 照合
- 駅データなし かつ 備考（LINEメモ）に駅名が含まれる → マッチ
- 駅データなし かつ 備考にも含まれない → **False**（駅指定がある場合は除外）

```python
def _match_station(engineer: dict, station: str) -> bool:
    if not station:
        return True  # 駅指定なし → 全員対象
    sta = _text_prop(engineer, PROP_STA)
    if sta:
        return station in sta
    memo = _text_prop(engineer, PROP_MEMO)
    if memo and station in memo:
        return True
    return False  # 駅データなし → 除外（駅指定がある照会なのでマッチさせない）
```

### BUG-4: engineer_query の案件フィルタ条件（L317-322）
**現状**
```python
_prj_filter = {
    "and": [
        {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}},
        {"property": PROP_RATE,   "number": {"greater_than": 0}},
    ]
}
```
**問題**: 「募集中」のみ。「選考中」案件（面談調整済み）はマッチング対象外になっている。

**修正**: 「募集中」と「選考中」の両方を含める。
```python
_prj_filter = {
    "or": [
        {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}},
        {"property": PROP_STATUS, "select": {"equals": VAL_ADJUSTING}},
    ]
}
# さらに単価>0はPythonレイヤでフィルタ（ORとANDの組み合わせはNotion APIで複雑になるため）
```
ただしNotion APIのOR+ANDネストは可能。シンプルに以下で対応:
```python
_prj_filter = {"property": PROP_RATE, "number": {"greater_than": 0}}
```
（ステータスフィルタはPythonレイヤで実施、VAL_RECRUITING と VAL_ADJUSTING の両方を通す）

## 実装手順（TASKS.md参照）
1. BUG-3 (_match_station) を修正
2. BUG-2 (_gross_threshold) を修正  
3. BUG-1 (_limit_reply) を修正
4. BUG-4 (engineer_query filter) を修正
5. `python line_query.py` でテスト実行（「HS 北小金」「H.S 北小金」「TK 渋谷」）
6. 構文チェック（python -m py_compile line_query.py）

## 禁止事項
- バグ修正以外のロジック変更禁止
- 既存のフォーマット出力変更禁止（単価/粗利表示は現行のまま）
- GROSS_THRESHOLDSの松野=5・岡本=3は変更禁止
"""

tasks = """# TASKS: line_query.py バグ修正

- [ ] 1. BUG-3: _match_station の return True -> return False に変更
- [ ] 2. BUG-2: GROSS_THRESHOLDS から「共通」削除、デフォルト5に変更
- [ ] 3. BUG-1: _limit_reply のヘッダー行数を動的化
- [ ] 4. BUG-4: engineer_query のフィルタを修正（選考中も対象に）
- [ ] 5. python -m py_compile line_query.py で構文チェック
- [ ] 6. python line_query.py でテスト（HS 北小金 / H.S 北小金 / TK 渋谷）
"""

import os

ses = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"

with open(os.path.join(ses, "SPEC_linequery_bugfix.md"), "w", encoding="utf-8") as f:
    f.write(spec)
with open(os.path.join(ses, "TASKS_linequery_bugfix.md"), "w", encoding="utf-8") as f:
    f.write(tasks)

print("SPEC + TASKS written")
print(f"  {ses}\\SPEC_linequery_bugfix.md")
print(f"  {ses}\\TASKS_linequery_bugfix.md")
