# SPEC.md — LINE Remote Command

最終更新: 2026-05-25

## 概要
スマホのLINEから「/run python matching_v2/matching_v2.py」のように送信すると、
PCのjobz-commandが実行して結果をLINEに返す機能を追加する。

## アーキテクチャ

```
LINE (スマホ)
  ↓ メッセージ送信
Cloud Run: webhook_server.py
  ↓ /run プレフィックス検出
remote_command_handler.py
  ↓ HTTP POST (30秒タイムアウト)
Cloudflare Tunnel (固定URL)
  ↓ トンネル
jobz-command: http://127.0.0.1:8765/run
  ↓ コマンド実行結果
Cloud Run → LINE返信
```

## 認証・セキュリティ
- 松野user_id（MATSUNO_USER_IDの値）からのみ /run 系コマンドを受け付ける
- jobz-commandへのリクエストに X-Auth-Token: {JOBZ_AUTH_TOKEN} を付与
- Cloudflare TunnelのURLは .env の JOBZ_COMMAND_URL から読む

## コマンド仕様

| 入力フォーマット | 動作 |
|---|---|
| /run <command> | jobz-commandの POST /run に転送 |
| /bg <command> | jobz-commandの POST /run_bg に転送（非同期） |
| /log | jobz-commandの GET /log を返す（直近50行） |
| /health | jobz-commandの GET /health を返す |

## 返信フォーマット
成功: "✅ 実行完了\n<結果の先頭200文字>"
失敗: "❌ エラー\n<エラー内容>"

## 環境変数（.envに追記する項目）
JOBZ_COMMAND_URL=https://xxxxx.trycloudflare.com
JOBZ_AUTH_TOKEN=jobz-terra-2026
# MATSUNO_LINE_USER_IDはすでに.envに存在する

## 実装対象ファイル
1. ses_work/line_webhook/remote_command_handler.py — 新規作成
2. ses_work/line_webhook/webhook_server.py — /runプレフィックス検出ロジックをprocess_message()の先頭に追記
3. ses_work/line_webhook/cloudflare/config.yml — Cloudflareトンネル設定テンプレート
4. ses_work/line_webhook/cloudflare/start_tunnel.bat — トンネル起動バッチ
5. ses_work/line_webhook/cloudflare/README_SETUP.md — 初回セットアップ手順書
6. ses_work/line_webhook/test_remote_command.py — 単体テスト

## remote_command_handler.py の詳細仕様

```python
import os, requests
from dotenv import dotenv_values

ENV_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
config = dotenv_values(ENV_PATH)
JOBZ_COMMAND_URL = os.environ.get('JOBZ_COMMAND_URL') or config.get('JOBZ_COMMAND_URL', '')
JOBZ_AUTH_TOKEN = os.environ.get('JOBZ_AUTH_TOKEN') or config.get('JOBZ_AUTH_TOKEN', 'jobz-terra-2026')
HEADERS = {"X-Auth-Token": JOBZ_AUTH_TOKEN, "Content-Type": "application/json"}
TIMEOUT = 30

def trim_result(text, max=200):
    return text[:max] + ("..." if len(text) > max else "")

def execute_remote(cmd):
    # POST /run {"cmd": cmd, "cwd": "ses_work"}
    # 返却: {"returncode":0,"stdout":"...","stderr":"..."}
    # → "✅ 実行完了\n<stdout先頭200文字>" or "❌ エラー\n<stderr>"

def execute_bg(cmd):
    # POST /run_bg {"cmd": cmd, "cwd": "ses_work"}
    # → "✅ バックグラウンド実行開始\n<cmd>"

def get_log():
    # GET /log
    # → 直近50行をLINEに返す（2000文字以内）

def get_health():
    # GET /health
    # → "✅ jobz-command: OK" or "❌ 接続失敗"
```

## webhook_server.py への追記位置
process_message()の先頭（text_stripped定義の直後）に以下を追記:

```python
# ── リモートコマンド（松野のみ） ─────────────────────────────────
if user_id and user_id == MATSUNO_USER_ID:
    if text_stripped.startswith("/run "):
        result = execute_remote(text_stripped[5:])
        reply_message(reply_token, result, sender_token)
        return
    elif text_stripped.startswith("/bg "):
        result = execute_bg(text_stripped[4:])
        reply_message(reply_token, result, sender_token)
        return
    elif text_stripped == "/log":
        result = get_log()
        reply_message(reply_token, result, sender_token)
        return
    elif text_stripped == "/health":
        result = get_health()
        reply_message(reply_token, result, sender_token)
        return
```

importに追記:
```python
from remote_command_handler import execute_remote, execute_bg, get_log, get_health
```

## Cloudflare config.yml テンプレート
```yaml
tunnel: TUNNEL_ID_HERE
credentials-file: C:\Users\ma_py\.cloudflared\TUNNEL_ID_HERE.json
ingress:
  - service: http://127.0.0.1:8765
  - service: http_status:404
```
※ hostnameは指定しない（Quick Tunnelでも動作する）

## README_SETUP.md の内容（セットアップ手順）
1. cloudflaredインストール: winget install Cloudflare.cloudflared
2. ログイン: cloudflared tunnel login
3. トンネル作成: cloudflared tunnel create jobz-command
4. 発行されたTUNNEL_IDをconfig.ymlに記入
5. start_tunnel.batを実行（またはスタートアップに登録）
6. 表示されたURL（trycloudflare.com）を.envのJOBZ_COMMAND_URLに記入
7. Cloud Runを再デプロイ: gcloud run deploy...
