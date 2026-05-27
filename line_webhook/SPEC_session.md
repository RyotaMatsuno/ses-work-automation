# SPEC.md - LINE Developerセッション保存スクリプト
# 作成: 2026-05-25

## 概要
2つのスクリプトを作成する。

### 1. save_session.py（手動実行用・初回1回だけ）
- Playwrightで実ブラウザ（headed）を起動
- LINE Developersコンソールのログインページを開く
- 岡本が手動でログイン完了するまで待機（input()で待つ）
- ログイン完了後、Cookieを `okamoto_session.json` に保存して終了

### 2. use_session.py（Jobzが呼び出す自動操作用）
- `okamoto_session.json` を読み込み
- headlessブラウザにCookieをセット
- https://developers.line.biz/console/ にアクセス
- ログイン済みかどうか確認（タイトルに"Console"が含まれるか）
- ログイン済みなら：
  - 指定チャンネルのWebhook設定ページに遷移
  - Webhook URLを設定・保存
  - 結果を標準出力に出力して終了
- ログイン済みでなければ：
  - "SESSION_EXPIRED" を出力して終了（再保存が必要）

## 引数（use_session.py）
- `--channel-id`: LINE チャンネルID
- `--webhook-url`: 設定するWebhook URL

## ファイルパス
- save_session.py: ses_work/line_webhook/save_session.py
- use_session.py: ses_work/line_webhook/use_session.py
- セッションファイル: ses_work/line_webhook/okamoto_session.json
