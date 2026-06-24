# GPT Wall-Hit: Investigation R P0 Triage
Date: 2026-06-22

## P0 Priority (GPT + Jobz agreed)

### Tier 0 — 即修正済（ジョブズ直接）
- P0-9: run_monthly_invoice.bat → v2に修正 ✅
- P0-10: NIGHTLY_BUDGET_USD → get_nightly_budget()関数化 ✅
- P0-6: skill_utils部分文字列 → トークンベース完全一致 ✅

### Tier 1 — Cursor作業指示（Task T）
- P0-2: CostGuard can_spend() fail-open → fail-close
- P0-1: Batch API CostGuard TOCTOU → reservation保持
- P0-5: reverse matching ANY → ALL-required + optional scoring
- P0-4: Cloud Run wrong line_query import → 統合

### Tier 2 — 後回し（セキュリティ）
- P0-7: command_server RCE → allowlist + shell=False
- P0-3: IMAP TLS → 証明書検証有効化
- P0-8: freee OAuth → env移行 + ローテーション

## P0-9 Invoice Impact Assessment
- SES_Freee_Invoiceスケジューラは run_monthly_invoice.bat を呼んでいた
- bat → freee_invoice_monthly.py --execute → 廃止済み(sys.exit(0))
- 前回実行5/25, exit code -2147020576 (エラー)
- 6/1請求書: v2手動実行の可能性あり → 松野確認必要
