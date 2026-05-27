# SPEC.md - 入金確認自動化

## 目的
毎月の請求書の入金状況をfreee APIで確認し、
支払期日を超過した未入金案件をLINEで松野に通知する。

## 処理フロー
1. freee APIで発行済み請求書一覧を取得
2. 各請求書の `payment_status` を確認
   - `paid` → 入金済み（スキップ）
   - `partially_paid` → 一部入金（アラート対象）
   - `unsettled` → 未入金（支払期日チェックへ）
3. `payment_due_date` が今日以前かつ未入金 → 未入金アラート対象
4. 通知済みフラグ（payment_notified.json）で重複通知を防ぐ
5. 松野公式LINEのPush APIで通知（通知内容: 会社名・請求金額・支払期日・超過日数）

## 通知内容フォーマット
```
【未入金アラート】
▶ {取引先名}
  請求額: {金額}円
  支払期日: {日付}（{N}日超過）
```
複数件ある場合は1通にまとめて送信

## --dry-runオプション
freee API取得まで実施・LINE送信スキップ

## スケジューラ登録
タスク名: freee_payment_check
毎月10日・20日・月末の3回実行（支払サイクルに合わせた定期チェック）

## 完了条件
1. py_compile確認
2. python freee/payment_checker.py --dry-run で正常終了
3. 入金済み・未入金の分類が正しいこと
