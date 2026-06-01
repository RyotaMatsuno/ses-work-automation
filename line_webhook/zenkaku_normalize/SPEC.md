# SPEC: LINEコマンド全角数字正規化

## 修正対象
`ses_work/line_webhook/line_query.py`

## 追加する関数
`detail_query` の直前に `normalize_number` 関数を追加する:

```python
def normalize_number(text: str) -> str:
    """全角数字・全角丸数字を半角数字に正規化する"""
    # 全角数字 → 半角数字
    text = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    # 全角丸数字 ①〜⑳ → 1〜20
    zenkaku_maru = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
    for i, c in enumerate(zenkaku_maru, 1):
        text = text.replace(c, str(i))
    return text
```

## 修正する箇所
`detail_query` 関数内の番号抽出を `normalize_number` 経由にする。

### 修正前
```python
def detail_query(text: str) -> str | None:
    """「詳細 ①」「詳細 6」などのコマンドを処理して案件全文を返す"""
    import re as _re
    # パターン: 詳細[スペース]番号
    m = _re.match(r'^詳細\s*([①-⑩\d]+)$', text.strip())
    if not m:
        return None
    num_str = m.group(1).strip()
    idx = _NUM_MAP.get(num_str)
    if idx is None:
        return f"「{num_str}」は無効な番号です。①〜⑩または1〜31で指定してください。"
```

### 修正後
```python
def detail_query(text: str) -> str | None:
    """「詳細 ①」「詳細 6」などのコマンドを処理して案件全文を返す"""
    import re as _re
    # パターン: 詳細[スペース]番号（全角数字・丸数字も正規化して受け付ける）
    m = _re.match(r'^詳細\s*(.+)$', text.strip())
    if not m:
        return None
    num_str = normalize_number(m.group(1).strip())
    idx = _NUM_MAP.get(num_str)
    if idx is None:
        return f"「{m.group(1).strip()}」は無効な番号です。①〜⑩または1〜31で指定してください。"
```

## 対応する入力パターン
| 入力例 | normalize_number後 | _NUM_MAP取得 |
|---|---|---|
| `詳細 1` | `1` | 0 ✅ |
| `詳細 10` | `10` | 9 ✅ |
| `詳細 １０` | `10` | 9 ✅ 新規 |
| `詳細 ①` | `1` | 0 ✅ (既存マップ経由) |
| `詳細 ⑩` | `10` | 9 ✅ (既存マップ経由) |
| `詳細 ⑮` | `15` | 14 ✅ 新規 |

## 注意
- `normalize_number` は `_NUM_MAP` の直前に定義する
- `_LAST_RESULTS` キャッシュや他のロジックは一切変更しない
