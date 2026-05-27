# CLAUDE.md - matching_v2 精度改善

## 禁止事項
- 既存の動作ロジック（スキル判定・スコア計算）を変更しない
- result.jsonのスキーマを後方互換を壊す形で変更しない
- 新規ファイルはmatching_v2/ディレクトリ内にのみ作成する

## 作業ルール
- 修正前後でpy_compile確認必須
- 変更行数は最小限に留める
- 変更したファイルは必ず変更内容をコメントで記述する

## 対象ファイル
- matching_v2/matching_v2.py（単価フィルタ・budget出力追加）
- matching_v2/notify_line.py（needs_check警告追加）
