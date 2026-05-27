# TASKS.md - attachment_importer v1 実装チェックリスト

## Phase 1: 環境セットアップ
- [ ] 1-1. ディレクトリ構成作成（parsers/ utils/ tests/ downloaded_files/）
- [ ] 1-2. 依存ライブラリインストール（openpyxl, python-docx, pdfplumber, anthropic, requests, python-dotenv）
- [ ] 1-3. utils/notion_writer.py の雛形作成（Notion API接続確認のみ）

## Phase 2: テキスト解析（text_parser.py）
- [ ] 2-1. 区切り線パターンによるブロック分割関数を実装
- [ ] 2-2. Claude APIによる1ブロックの構造化抽出を実装
- [ ] 2-3. 複数ブロックに対してループ処理を実装
- [ ] 2-4. サンプルテキスト（①②形式）でテスト: python -m pytest tests/test_text_parser.py
- [ ] 2-5. テスト結果確認（3名分抽出できること）

## Phase 3: ファイル解析（file_parser.py）
- [ ] 3-1. Excelファイル（.xlsx/.xls）のテキスト抽出を実装
- [ ] 3-2. Wordファイル（.docx）のテキスト抽出を実装
- [ ] 3-3. PDFファイルのテキスト抽出を実装
- [ ] 3-4. Googleスプレッドシート URL のダウンロード処理を実装（drive_downloader.py）
- [ ] 3-5. 抽出テキストをClaude APIで構造化する処理を実装（text_parserのプロンプト再利用）
- [ ] 3-6. 各形式でpython -m py_compileによる構文確認

## Phase 4: マージ処理（importer.py）
- [ ] 4-1. テキスト解析結果とファイル解析結果の氏名マッチング関数を実装
- [ ] 4-2. マージ（ファイル情報優先）処理を実装
- [ ] 4-3. 突合失敗時のフォールバック処理を実装

## Phase 5: Notion登録（notion_writer.py）
- [ ] 5-1. 重複チェック（名前でエンジニアDB検索）を実装
- [ ] 5-2. スキルのmulti_selectオプション名への変換処理を実装
- [ ] 5-3. 新規登録処理を実装（SPEC.mdのフィールドマッピング通り）
- [ ] 5-4. 更新処理を実装
- [ ] 5-5. 担当者の自動判定（source→担当者名）を実装
- [ ] 5-6. エラー時のfailed_imports.json保存を実装

## Phase 6: メインスクリプト（importer.py）
- [ ] 6-1. CLIオプション実装（--text / --file / --spreadsheet-url / --source）
- [ ] 6-2. 全フローの結合（テキスト解析→ファイル解析→マージ→Notion登録）
- [ ] 6-3. import.logへのログ出力を実装
- [ ] 6-4. dry-runオプションを追加（--dry-run: Notionに書かずログだけ出力）

## Phase 7: skill_judge.py修正（matching_v2）
- [ ] 7-1. skill_judge.pyにfile_parser.pyのテキスト抽出関数をimport
- [ ] 7-2. スキル情報参照の優先順位ロジックを実装
     （添付ファイルパス > DriveリンクURL > 人員情報原文 > スキルmulti_select）
- [ ] 7-3. 修正後にpython -m py_compile で構文確認

## Phase 8: mail_pipeline.py修正
- [ ] 8-1. classify_email()の人員情報判定ロジックを確認
- [ ] 8-2. 添付ファイルありの場合にimporter.pyを呼び出す処理を追加
- [ ] 8-3. python -m py_compile で構文確認

## Phase 9: エンドツーエンドテスト（dry-run）
- [ ] 9-1. サンプルテキスト①（H.S 1名）でdry-run実行・ログ確認
- [ ] 9-2. サンプルテキスト②（OA/R.H/U.H 3名）でdry-run実行・ログ確認
- [ ] 9-3. エラーケース（ファイルなし）でdry-run実行・ログ確認

## 完了確認
- [ ] import.logに正常出力されること
- [ ] python -m py_compile で全ファイルが構文エラーなし
- [ ] SPEC.mdの全要件が実装されていること
