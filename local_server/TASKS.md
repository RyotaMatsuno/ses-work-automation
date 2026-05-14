# TASKS.md — ジョブズ コマンドサーバー 実装チェックリスト

最終更新: 2026-05-08

## フェーズ1: コアサーバー構築
- [x] `local_server/` ディレクトリ作成
- [x] `command_server.py` 作成（HTTPサーバー本体）
  - [x] GET /health エンドポイント
  - [x] POST /run エンドポイント
  - [x] POST /write_and_run エンドポイント
  - [x] localhost限定バインド
  - [x] AUTH_TOKENによる認証
  - [x] server.logへのログ出力
- [x] `start_server.bat` 作成

## フェーズ2: MCPブリッジ構築
- [x] `mcp_bridge.py` 作成
  - [x] run_command ツール定義
  - [x] write_and_run ツール定義
  - [x] command_serverへのHTTP POSTブリッジ
- [x] `claude_desktop_config.json` に `jobz-command` を追加

## フェーズ3: 依存関係・起動確認
- [x] `pip install mcp` 実行
- [x] `command_server.py` 単体起動テスト
  - [x] GET /health で {"status":"ok"} が返ること
  - [x] POST /run で `python --version` が実行できること
- [x] Claude Desktop 再起動 → 新規チャットで `jobz-command` ツールが表示されること
- [x] ジョブズから `run_command` で `python --version` を実行できること（Python 3.12.10 確認済み）

## フェーズ4: スタートアップ自動起動設定
- [x] `start_server.bat` をスタートアップフォルダに登録
- [x] start_server.bat改修: 起動前に旧プロセス自動kill（多重起動防止）（2026-05-08）
- [ ] PC再起動後に自動でサーバーが起動することを確認（次回再起動時に検証）

## フェーズ5: 実運用テスト
- [x] ジョブズから `run_command` で `echo` 実行 → 正常動作確認（2026-05-08）
- [ ] ジョブズから `pip install requests` を実行
- [ ] ジョブズから `git status` を実行（ses_workディレクトリ）
- [ ] ジョブズから `write_and_run` でスクリプト作成→即実行
- [ ] 既存の `matching.py` をジョブズが起動できることを確認

## 完了条件
- [x] 松野がターミナルを開かずにジョブズが全コマンドを実行できる状態
- [ ] PC起動時にサーバーが自動起動している状態（次回再起動で確認）

---

## 運用メモ
- AUTH_TOKEN: `jobz-terra-2026`
- サーバーURL: `http://127.0.0.1:8765`
- ログ: `C:\Users\ma_py\OneDrive\デスクトップ\ses_work\local_server\server.log`
- Python: 3.12.10 確認済み（2026-05-08）
- 問題が出たらログを確認してからジョブズに報告する

## トラブル履歴
| 日付 | 症状 | 原因 | 対処 |
|---|---|---|---|
| 2026-05-08 | WinError 10061 接続拒否 | 旧プロセスが8765ポートを複数掴んでいた | taskkillで手動kill → bat改修で自動kill化 |
