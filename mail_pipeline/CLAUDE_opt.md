# CLAUDE.md - mail_pipeline コスト最適化改修

## 作業ディレクトリ
C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\

## 対象ファイル
- mail_pipeline.py（既存・1025行）
- 改修後も同じファイル名で上書き保存

## 絶対禁止事項
- claude-sonnet / claude-opus の使用禁止。claude-haiku-4-5-20251001 のみ使用
- anthropic Python SDKは使わない。requests で直接 Anthropic REST API を呼ぶ
- Batch APIを使う（分類・抽出・マッチング）。通常API呼び出しはLINE送信トリガーのみ
- 既存の関数名・引数シグネチャを変えない（register_project, register_engineer, ai_matching等）
- process_skill_sheet, extract_affiliation 等の既存関数を削除しない
- config/.env の読み込み方法を変えない（dotenv_values継続）
- processed_ids.json の処理ロジックを変えない

## コーディングルール
- Python 3.10+, UTF-8
- ファイル先頭に sys.stdout.reconfigure(encoding='utf-8', errors='replace') を維持
- 既存の log() 関数を必ず使う（print直接使用禁止）
- エラーは握りつぶさずログ記録
- 改修後は python -m py_compile mail_pipeline.py で構文チェック必須

## 変更の最小化原則
- 既存の動作を壊さない
- 変更するのは classify_email 関数と main の処理ループのみ
- 他の関数は一切変更しない
