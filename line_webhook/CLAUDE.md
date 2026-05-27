# CLAUDE.md — LINE Remote Command

## 役割
LINE → Cloud Run → Cloudflare Tunnel → jobz-command (port 8765) の疎通を実現する。
スマホのLINEからPCにコマンドを送り、結果をLINEに返す。

## 禁止事項
- jobz-commandのauth token（jobz-terra-2026）をログに出力しない
- Cloudflare Tunnel URLを.envなしでハードコードしない
- webhook_server.pyの既存ロジックを壊さない（追記のみ）
- 27分超の処理をjobz-commandに投げない（ハングする）
- 外部からの任意コマンド実行は松野user_idからのみ許可

## ファイル構成ルール
- 既存: `ses_work/line_webhook/webhook_server.py` に追記
- 新規: `ses_work/line_webhook/remote_command_handler.py`（コマンド処理分離）
- .envに追記: `JOBZ_COMMAND_URL` / `JOBZ_AUTH_TOKEN`
- Cloudflareトンネル設定: `ses_work/line_webhook/cloudflare/config.yml`

## コーディングルール
- Python 3.11
- 既存のimportを壊さない
- エラーは必ずLINEに返信（サイレント失敗禁止）
- タイムアウトは30秒（jobz-commandのレスポンス待ち）
- コマンド実行結果は先頭200文字のみLINEに返す（メッセージ上限対策）

## webhook_server.py の現状把握（重要）
- process_message()関数の先頭に /run 系コマンド処理を追記する
- user_idはhandle_webhook()からprocess_message()に渡されている（引数名: user_id）
- MATSUNO_USER_IDはos.environ経由で取得済み
- push_message() / reply_message()はすでに実装済みなので再利用すること
