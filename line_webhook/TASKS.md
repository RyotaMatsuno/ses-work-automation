# TASKS.md — LINE Remote Command

## Phase 1: remote_command_handler.py 作成
- [ ] ses_work/line_webhook/remote_command_handler.py を新規作成
- [ ] ENV_PATHから JOBZ_COMMAND_URL / JOBZ_AUTH_TOKEN を読み込む（os.environ優先、fallback .env）
- [ ] trim_result(text, max=200) を実装
- [ ] execute_remote(cmd) を実装 → POST /run → "✅ 実行完了\n<stdout200文字>" or "❌ エラー\n<stderr>"
- [ ] execute_bg(cmd) を実装 → POST /run_bg → "✅ バックグラウンド実行開始\n<cmd>"
- [ ] get_log() を実装 → GET /log → 直近50行・2000文字以内
- [ ] get_health() を実装 → GET /health → "✅ jobz-command: OK" or "❌ 接続失敗: <error>"
- [ ] 全関数にtimeout=30・try/except実装

## Phase 2: webhook_server.py に追記
- [ ] ファイル先頭のimport群に `from remote_command_handler import execute_remote, execute_bg, get_log, get_health` を追記
- [ ] process_message()内のtext_stripped定義直後（print文の次行）に /run 系コマンド分岐を追記
- [ ] user_id == MATSUNO_USER_ID のガード条件を必ず入れる
- [ ] /run, /bg, /log, /health の4コマンドを実装
- [ ] 既存ロジックを一切変更しない（追記のみ）

## Phase 3: Cloudflare設定ファイル生成
- [ ] ses_work/line_webhook/cloudflare/ ディレクトリ作成
- [ ] config.yml テンプレートを作成（TUNNEL_ID_HEREプレースホルダー）
- [ ] start_tunnel.bat を作成（`cloudflared tunnel --config config.yml run jobz-command`）
- [ ] README_SETUP.md を作成（SPEC.mdの手順7ステップを記載）

## Phase 4: テストスクリプト
- [ ] ses_work/line_webhook/test_remote_command.py を作成
- [ ] JOBZ_COMMAND_URLが未設定の場合はlocalhost:8765で試行
- [ ] get_health()を呼んで結果を print するだけのシンプルなテスト
- [ ] python test_remote_command.py で単体実行できること
