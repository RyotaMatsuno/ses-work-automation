# TASKS: line_query.py バグ修正

- [x] 1. BUG-3: _match_station の return True -> return False に変更
- [x] 2. BUG-2: GROSS_THRESHOLDS から「共通」削除、デフォルト5に変更
- [x] 3. BUG-1: _limit_reply のヘッダー行数を動的化
- [x] 4. BUG-4: engineer_query のフィルタを修正（選考中も対象に）
- [x] 5. python -m py_compile line_query.py で構文チェック
- [x] 6. python line_query.py でテスト（HS 北小金 / H.S 北小金 / TK 渋谷）
