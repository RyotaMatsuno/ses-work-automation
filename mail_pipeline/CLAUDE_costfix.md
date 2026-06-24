# CLAUDE_costfix.md
# mail_pipeline コスト暴走修正

## 作業ルール
- 修正対象: mail_pipeline.py のみ
- バックアップ: 修正前に mail_pipeline.py.bak_costfix を作成してから編集
- 変更箇所はコメント `# [COSTFIX]` を付けて明示
- 既存のロジック（分類・Notion登録・マッチング・提案文生成）は一切触らない
- テスト: DRY_RUN=1 で構文エラーがないことを確認してから終了
- 日本語のprint/logは utf-8 で書く（cp932エラー回避のためf文字列内に絵文字不使用）

## 禁止事項
- PROCESS_LIMIT / FETCH_LIMIT 以外の定数変更
- classify_email / classify_email_v2 / ai_matching / double_check の変更
- Notion登録・メール送信ロジックの変更
- 新しいimportの追加（標準ライブラリのみ許可）
