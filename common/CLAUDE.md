# Phase2: 共有コストレジャー - Codex作業ルール
## 作業対象
- `common/__init__.py` を新規作成（空ファイル）
- `common/ledger.py` を新規作成

## 禁止事項
- 他のファイルを変更しない
- 依存ライブラリを増やさない（stdlib + json + pathlib のみ）

## 完了条件
- `python -c "from common.ledger import can_spend, record; print('ok')"` がseswork起動で通ること
- TASKS.mdのチェックリストが全て[x]
