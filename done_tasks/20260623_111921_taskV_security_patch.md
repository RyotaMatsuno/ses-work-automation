# 【Cursor作業指示】Task V: セキュリティ緊急パッチ（P0-7/P0-8/P0-3）

対象ディレクトリ: ses_work/
作業内容: セキュリティ上の致命的問題3件を一括修正
参照ファイル: CLAUDE.md / INVESTIGATION_REPORT.md
完了条件: 全3件の修正完了 + 各修正のテスト通過
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## P0-7: command_server セキュリティ強化
場所: local_server/command_server.py

修正内容:
1. `shell=True` を `shell=False` に変更（引数はリスト形式で渡す）
2. コマンドallowlistを実装（python, pip, rg, echo, type, dir のみ許可）
3. トークンを環境変数化（config/.env の JOBZ_COMMAND_TOKEN に移行）
4. localhostバインドの明示的検証追加（Host headerチェック）
5. remote_command_handler.py のCloudflareトンネル関連コードを削除

テスト:
- allowlist外のコマンドが拒否されること
- shell injection（; rm -rf /等）が不可能なこと
- localhost以外からのアクセスが拒否されること

## P0-8: freee OAuth secret のソース除去
場所: freee_auth/token_manager.py:12-14

修正内容:
1. client_id, client_secret をソースコードから完全除去
2. config/.env から読み込む方式に変更（FREEE_CLIENT_ID, FREEE_CLIENT_SECRET）
3. .gitignore に config/.env が含まれていることを確認
4. 既にソースにハードコードされていた値は、松野がfreee管理画面からsecretを再発行した後に無効化される前提

注意: secret再発行は松野の手動操作。Cursorは.envからの読み込みへの移行のみ行う。

## P0-3: IMAP TLS証明書検証の有効化
場所: mail_pipeline/mail_pipeline.py:558-560

修正内容:
1. `ssl.CERT_NONE` を `ssl.CERT_REQUIRED` に変更
2. `check_hostname=False` を `check_hostname=True` に変更
3. 開発環境用に環境変数 `IMAP_SKIP_TLS_VERIFY=1` で無効化可能にする（本番では未設定）
4. 証明書検証エラー時のログ出力を追加

テスト:
- mail65.onamae.ne.jp:993 への接続が正常に動作すること
- 不正な証明書での接続が拒否されること
