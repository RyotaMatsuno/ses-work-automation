# TASKS.md - flag_auto_updater 実装チェックリスト

## Phase 1: セットアップ
- [x] ses_work/flag_auto_updater/ ディレクトリ作成
- [x] ses_work/flag_auto_updater/__init__.py 作成
- [x] ses_work/flag_auto_updater/logs/ ディレクトリ作成
- [x] ses_work/flag_auto_updater/run_flag_updater.py 作成（entrypoint）
- [x] ses_work/flag_auto_updater/notion_client.py 作成（Notion REST APIラッパー）
- [x] ses_work/flag_auto_updater/rule_engine.py 作成（除外ルール判定ロジック）

## Phase 2: notion_client.py 実装
- [x] .envからNOTION_API_KEY読み込み
- [x] get_database_schema(db_id) → プロパティ名:型 の dict を返す
- [x] ensure_properties(db_id, required_props) → 不足プロパティをPATCH /databases/{id}で追加
- [x] get_all_engineers(db_id) → 全ページネーション対応で全件リスト返す
- [x] update_engineer_flag(page_id, flag: bool, reason: str) → PATCH /pages/{id}

## Phase 3: rule_engine.py 実装
- [x] KANTO_PREFECTURES 定数定義
- [x] BLANK_DAYS_THRESHOLD = 365 定数定義
- [x] extract_prop(engineer, name, prop_type) → プロパティ値を安全に取得するヘルパー
- [x] judge_engineer(engineer) → (is_target: bool, reasons: list[str]) を返す
  - [x] 外国籍チェック
  - [x] 地方人材チェック
  - [x] ブランクチェック
  - [x] 短期連続フラグチェック
  - [x] 既往歴フラグチェック

## Phase 4: run_flag_updater.py 実装
- [x] run_flag_updater() 関数実装
  - [x] Step 0: ログ設定（ファイル + コンソール）
  - [x] Step 1: ensure_properties でプロパティ自動作成
  - [x] Step 2: get_all_engineers で全件取得
  - [x] Step 3: judge_engineer で全件判定
  - [x] Step 4: update_engineer_flag で全件更新（rate limit sleep込み）
  - [x] Step 5: サマリーログ出力（総件数/対象件数/除外件数/除外者一覧）
- [x] if __name__ == "__main__": run_flag_updater() で単体実行対応

## Phase 5: matching_v3統合
- [x] ses_work/matching_v3/matching_v3.py の冒頭に run_flag_updater() 呼び出しを追加
- [x] import パスが通ることを確認（sys.path調整が必要な場合は対応）

## Phase 6: テスト
- [x] ses_work/flag_auto_updater/tests/test_rule_engine.py 作成
  - [x] 外国籍エンジニア → False
  - [x] 地方エンジニア（大阪） → False
  - [x] ブランク30日 → True（閾値以内）
  - [x] ブランク61日 → False（閾値超）
  - [x] 短期連続フラグTrue → False
  - [x] 既往歴フラグTrue → False
  - [x] 全条件クリア → True
  - [x] 複数除外理由が重なる場合の理由文字列確認
- [x] pytest tests/test_rule_engine.py → 全パス確認
- [x] python run_flag_updater.py を手動実行してログ確認

## Phase 7: 完了確認
- [x] Notionエンジニアページで「提案対象フラグ」「除外理由」カラムが更新されていること
- [x] 除外対象エンジニアのフラグがFalseになっていること（初回実行時は国籍/居住地未入力のため除外0件）
- [x] ログファイルにサマリーが出力されていること
- [ ] matching_v3と統合後、8:00自動実行で正常完走すること
