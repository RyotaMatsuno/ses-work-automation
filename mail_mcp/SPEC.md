# SPEC: ses-mail Python REST化 (mail_rest.py)
最終更新: 2026-06-12

## 目的
ブラウザ版Claude.aiからjobz-command(/run)経由でIMAP操作を可能にするCLIラッパー。

## 対応アカウント
- matsuno : r-matsuno@terra-ltd.co.jp / mail65.onamae.ne.jp:993
- okamoto : r-okamoto@terra-ltd.co.jp / mail65.onamae.ne.jp:993
- sessales: sessales@terra-ltd.co.jp  / mail65.onamae.ne.jp:993

## CLIアクション
- fetch   : 未読メール取得 (--account, --limit, --folder)
- search  : キーワード検索 (--account, --query, --limit)
- mark_read: 既読マーク   (--account, --uid)
- list_folders: フォルダ一覧 (--account)

## 呼び出し方法
jobz-command経由:
  POST http://127.0.0.1:8765/run
  {"command": "python mail_mcp/mail_rest.py fetch --account matsuno --limit 10"}

直接実行:
  cd X:\  (subst X: ses_work)
  python mail_mcp/mail_rest.py fetch --account sessales --limit 5

## SSL設定
onamaeサーバーの証明書検証を緩和（mail_server.pyと同設定）。
内部呼び出し専用のため許容。

## 完了条件
- sessales fetch/search/list_folders: ✅ 2026-06-12確認
- matsuno  fetch/list_folders       : ✅ 2026-06-12確認
- okamoto                           : ✅ 2026-06-12確認
