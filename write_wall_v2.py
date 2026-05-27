spec = '''# SPEC_wall_v2.md — 壁打ちスクリプト更新

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
'''

tasks = '''# TASKS_wall_v2.md

- [ ] 1. wall_hitting.pyにDEFAULT_OPENAI_MODEL / SEARCH_OPENAI_MODELの定数追加
- [ ] 2. argparseに --search フラグ追加（store_true）
- [ ] 3. fetch_openai()または呼び出し元でmodelを引数から切り替え
- [ ] 4. py_compile wall_hitting.py 確認
- [ ] 5. python wall_hitting.py --problem "テスト" --search で正常終了確認
'''

with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\SPEC_wall_v2.md', 'w', encoding='utf-8') as f:
    f.write(spec)
with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\TASKS_wall_v2.md', 'w', encoding='utf-8') as f:
    f.write(tasks)
print("written", flush=True)
