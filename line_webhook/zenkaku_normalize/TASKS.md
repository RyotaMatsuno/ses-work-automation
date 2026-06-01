# TASKS.md — zenkaku_normalize

## 実装チェックリスト

- [ ] T1: `line_webhook/line_query.py` の `_NUM_MAP` 直前に `normalize_number` 関数を追加する
- [ ] T2: `detail_query` の正規表現を `r'^詳細\s*(.+)$'` に変更し、`normalize_number` を経由してから `_NUM_MAP.get()` する
- [ ] T3: エラーメッセージの `num_str` を元の入力文字列に戻す（`m.group(1).strip()`）
- [ ] T4: `python -c "import sys; sys.path.insert(0,'line_webhook'); from line_query import normalize_number, detail_query; print('OK')"` が通ることを確認
- [ ] T5: 動作確認スクリプト `zenkaku_normalize/test_normalize.py` を作成して実行する

## テスト内容（T5）
```python
import sys
sys.path.insert(0, 'line_webhook')
from line_query import normalize_number

cases = [
    ('１０', '10'),
    ('⑮', '15'),
    ('①', '1'),
    ('５', '5'),
    ('10', '10'),
    ('1', '1'),
]
for inp, expected in cases:
    result = normalize_number(inp)
    status = '✅' if result == expected else '❌'
    print(f'{status} normalize_number("{inp}") = "{result}" (expected "{expected}")')
```
