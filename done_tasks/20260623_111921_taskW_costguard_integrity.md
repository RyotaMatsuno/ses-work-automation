# 【Cursor作業指示】Task W: CostGuard整合性改善（P0-2/P0-1）

対象ディレクトリ: ses_work/
作業内容: CostGuardのfail-open問題とTOCTOU問題を修正
参照ファイル: CLAUDE.md / INVESTIGATION_REPORT.md
完了条件: fail-close動作の確認 + batch予約の整合性テスト通過
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## P0-2: CostGuard fail-open → fail-close
場所: cost_guard.py:680-683

修正内容:
1. `can_spend()` 内のDB読み取り例外時に `budget_ok = False` に変更
2. 例外発生時にevent_logに `reason='db_error_blocked'` を記録
3. fail-close動作であることをdocstringに明記

テスト:
- ledger DB破損/ロック時に `allowed()` が False を返すこと
- event_logに適切な記録が残ること

## P0-1: Batch API CostGuard TOCTOU修正
場所: mail_pipeline/mail_pipeline.py:699-713

現状の問題:
- `allowed()` で予約後すぐ `finalize(transient)` し、実コストは後から `ledger_record()`
- 並列バッチで予約→即解放→別プロセスが同じ枠を使う可能性

修正内容:
1. batch完了まで reservation を保持する設計に変更
2. `allowed()` で予約取得 → batch API完了 → `finalize(success=True, actual_tokens=...)` の流れに統一
3. batch失敗時は `finalize(success=False)` で予約解放
4. reservation timeout（10分）を追加し、orphaned reservationの自動解放を実装

テスト:
- 正常batch: 予約→実行→finalize(success)の一連の流れ
- 失敗batch: 予約→失敗→finalize(failure)で予約解放
- timeout: 10分経過後にorphaned reservationが解放されること
