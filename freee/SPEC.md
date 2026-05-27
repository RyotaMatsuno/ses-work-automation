# SPEC.md — freee請求書タスクスケジューラ自動実行

## 目的
毎月1日 9:00 に freee_invoice_v2.py を自動実行し、請求書ドラフトを自動作成する。

## 実装内容

### 1. run_invoice.bat 作成
- パス: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\run_invoice.bat
- 内容: python freee_invoice_v2.py を実行し、ログをファイルに出力

### 2. Windowsタスクスケジューラ登録
- タスク名: freee_auto_invoice
- トリガー: 毎月1日 09:00
- 実行: run_invoice.bat
- ログ出力先: C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee\invoice_auto.log
- schtasks コマンドで登録（GUIなし）

## 完了条件
- schtasks /query で freee_auto_invoice が表示される
- run_invoice.bat を手動実行してfreee_invoice_v2.pyが正常起動する
