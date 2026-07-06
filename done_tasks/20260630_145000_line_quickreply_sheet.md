# 【Cursor作業指示】LINE登録フロー改善: クイックリプライ2択 + スプレッドシートURL解析

## 対象
ses_work/line_webhook/

## 背景
タスクCのセッション管理基盤は完成済。追加で以下を実装:
- サマリー受信時にLINEクイックリプライ(2択ボタン)で形式確認
- スプレッドシートURLの自動検出・解析

## 1. クイックリプライ実装
サマリー受信→仮登録後のLINE返信にquickReply追加:
- ボタン1: "Excel/Word/パワポ" (text: "ファイル送信")
- ボタン2: "スプレッドシートURL" (text: "スプレッドシート")

## 2. 分岐処理

### "ファイル送信"受信
- セッション状態をwaiting_fileに更新
- 返信: "スキルシート(Excel/Word/パワポ)を送信してください(30分以内)"
- ファイル受信→既存セッション紐付けに合流

### "スプレッドシート"受信
- サマリーテキストからURL検出
  - 正規表現: https://docs.google.com/spreadsheets/d/[a-zA-Z0-9_-]+
- URLあり:
  - sheet_fetcher.pyのfetch_sheet_text()を流用(mail_attachment_importerからimport)
  - OAuth2: line_webhook/config/drive_token.json
  - 取得成功 → skill_extractorで解析 → Notion更新
  - 権限エラー → "スプレッドシートにアクセスできません。Excel/Wordで送ってください" + waiting_fileに切替
- URLなし:
  - "サマリーにURLが見つかりません。URLを含めて送り直すか、Excel/Wordで送信してください"

## 3. セッション状態拡張
pending → waiting_file or processing_sheet → done

## 4. sheet_fetcher.pyの共有化
mail_attachment_importer/sheet_fetcher.pyをline_webhookからimport可能にする

## 参照
- CLAUDE.md
- webhook_server.py(セッション管理部分)
- skill_extractor.py
- mail_attachment_importer/sheet_fetcher.py

## 完了条件
- [ ] クイックリプライ2択が表示
- [ ] Excel/Word選択→ファイル待機→受信→登録
- [ ] スプレッドシート選択→URL検出→Sheets API取得→登録
- [ ] 権限エラー時フォールバック
- [ ] 既存テスト通過 + 新規テスト
