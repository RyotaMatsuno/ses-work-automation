# CLAUDE.md - 請求書自動送付

## 禁止事項
- freee_invoice_v2.pyを改変しない
- 既存のtoken_manager.pyを改変しない
- 送信実行前に必ず--dry-runで動作確認すること

## 作業ルール
- credentialはconfig/.envからdotenv_valuesで読み込む
- py_compile確認必須
- ログはlogs/invoice_send.logに出力

## 対象ファイル
- freee/invoice_sender.py（新規）
