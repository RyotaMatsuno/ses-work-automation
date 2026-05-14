# CLAUDE.md - LINE Webhook 自動化PJ

最終更新: 2026-05-08

## プロジェクト概要
LINEで届いた案件・人材情報を自動でNotion登録 → マッチング → ダブルチェック → LINE返信するシステム。
岡本・松野ともに「確認して送信して」と言うだけで完結させることが目標。

## 技術スタック
- Python 3.12
- Flask（Webサーバー）
- Cloud Run（ホスティング）
- Anthropic API（Claude Sonnet 4）
- Notion API
- LINE Messaging API

## ファイル構成
- `webhook_server.py` : メインサーバー（松野: /webhook、岡本: /webhook_okamoto）
- `../double_check/double_check.py` : ダブルチェックロジック（関数として呼び出す）
- `../config/.env` : 環境変数
- `../matching.py` : 単体マッチングスクリプト（参考用）

## 作業ルール
- webhook_server.py を直接編集する
- double_check.py はインポートして使う（コピーしない）
- 環境変数は ../config/.env から読む
- デプロイは deploy_cloudrun.bat で行う

## 禁止事項
- 送信系（LINE返信・メール送信）を確認なしで実行しない
- エンジニア単価・粗利計算を省略しない
- ダブルチェックをスキップしない
- 3点セットなしで実装開始しない
