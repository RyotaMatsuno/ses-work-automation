# SPEC_wall_v2.md — 壁打ちスクリプト更新

## 変更内容
wall_hitting.pyに以下を追加する。

### 1. --search フラグ追加
- `--search` フラグがある場合: OpenAIのモデルを `gpt-4o-search-preview` に切り替える
- フラグがない場合: 従来通り `gpt-4o`

### 2. モデル定数を変数化
- DEFAULT_OPENAI_MODEL = "gpt-4o"
- SEARCH_OPENAI_MODEL = "gpt-4o-search-preview"
- args.searchがTrueなら SEARCH_OPENAI_MODEL を使う

## 変更対象ファイル
- wall_hitting.py のみ修正

## 完了条件
- py_compile wall_hitting.py エラーなし
- python wall_hitting.py --problem "テスト" --search が正常終了
