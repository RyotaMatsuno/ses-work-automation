# CLAUDE.md - 入金確認自動化

## 禁止事項
- freee_invoice_v2.py / invoice_sender.py / token_manager.py を改変しない
- 送信系（LINE送信）をこのスクリプト内で完結させない（notify_line.pyを呼ぶ形にする）
- 未入金アラートを連続で送り続けない（1日1回チェック、通知済みフラグを持つ）

## 作業ルール
- credentialはconfig/.envからdotenv_valuesで読み込む
- py_compile確認必須
- ログはlogs/payment_check.logに出力

## 対象ファイル
- freee/payment_checker.py（新規）
