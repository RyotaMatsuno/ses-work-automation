# SPEC.md - 請求書自動送付

## 目的
freeeで毎月1日に自動生成された請求書をPDFで取得し、クライアントへメール送付する。

## 処理フロー
1. freee APIで当月発行済みの請求書一覧を取得
2. 各請求書のPDFをダウンロード（freee `/api/1/invoices/{id}/download`）
3. ses-mail MCPでクライアントへメール送信（松野アドレスまたはsessales）
4. 送付完了をNotionの対応レコードに記録

## 送信元アドレス判定
- 松野担当クライアント → r-matsuno@terra-ltd.co.jp
- 岡本担当クライアント → r-okamoto@terra-ltd.co.jp
- 共通 → sessales@terra-ltd.co.jp

## メール本文
件名: 【請求書】{year}年{month}月分 {会社名}
本文: シンプルな請求書送付の定型文（請求書PDF添付）

## --dry-runオプション
PDF取得まで実施・メール送信はスキップしてログ出力のみ

## スケジューラ登録
freee_auto_invoiceタスク（毎月1日09:00）の後続として、
別タスク「freee_invoice_send」として毎月1日10:00に登録

## 完了条件
1. py_compile確認
2. python freee/invoice_sender.py --dry-run で請求書PDF取得確認
3. 取得した請求書リストと送付先が正しいこと
