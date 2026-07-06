# TASKS.md - cost_guard_v2 実装チェックリスト

最終更新: 2026-06-17 / バージョン: v2.10
対応SPEC: SPEC.md v2.10

---

## Phase 0: 準備

- [x] 0.1 `.env` に SPEC §13 の新規定数全てを追加(STATE_DIR / DEDUP_CLAIM_TTL_SEC 含む)
- [x] 0.2 既存 `.env` の `COST_DAILY_LIMIT` / `COST_MONTHLY_LIMIT` を `COST_GUARD_*_USD` に統一
- [ ] 0.3 `git checkout -b feature/cost_guard_v2.4` でブランチ作成
- [x] 0.4 sqlite3 移行スクリプト `migrations/migrate_to_sqlite_v2.4.py` 作成
- [x] 0.5 既存 `cost_state.json` を `cost_state.json.bak_v2.4` にバックアップしてから sqlite へ移行
- [x] 0.6 `config/dedup_target_required.json` 新規作成(SPEC §5.4)
- [x] 0.7 `config/model_rates.json` を確認、未登録モデル一覧を `cost_guard_v2/unknown_models.md` に記録

## Phase 1: 並行制御(sqlite採用、最優先)

- [x] 1.1 `common/state_store.py` 新規作成
  - sqlite3 接続管理、`BEGIN IMMEDIATE` トランザクションヘルパ
  - SPEC §8.2 の **7テーブル**(daily_state / monthly_state / phase_calls / reservations / dedup_claims / dedup_claims_archive / event_log: 列に script を含む)を `init_schema()` で作成
- [x] 1.2 timeout=5秒、超過時 reason=error_internal を返すロック処理
- [x] 1.3 既存 `common/ledger.py` の `_load_state` / `_save_state` を sqlite 経由に置換
  - 既存 can_spend/record/daily_total/monthly_total のシグネチャは温存
- [x] 1.4 移行スクリプトの実行 → 既存 json から sqlite への移行検証
- [x] 1.5 真実源マッピング(SPEC §8.4)をコメントに明記

## Phase 2: 装置1 - フェーズ別モデル選択 + 予約方式

- [x] 2.1 `common/ledger.py` に `reserve(phase: str) -> str | None` 実装
- [x] 2.2 `common/ledger.py` に `release(reservation_id)` 実装
- [x] 2.3 `common/ledger.py` に `record()` を kwargs 拡張(SPEC §11.2)
- [x] 2.3b `common/ledger.py` の `record()` 内で `reservation_id` 指定時に phase_calls.reserved -= 1 / consumed += 1 / reservations.finalized=1 を BEGIN IMMEDIATE 内で原子的に実行(SPEC §3.2.1)
- [x] 2.3c `common/ledger.py` の `release()` 内で phase_calls.reserved -= 1 / reservations.finalized=1 を BEGIN IMMEDIATE 内で実行(consumed は加算しない、SPEC §3.2.1)
- [x] 2.3d `common/ledger.py` に内部 `_record_in_tx(conn, ...)` / `_release_in_tx(conn, ...)` / `_confirm_dedup_in_tx(conn, ...)` / `_release_dedup_in_tx(conn, ...)` を実装(SPEC §3.2.2、public エントリは単独使用時のみ自前 BEGIN IMMEDIATE)
- [x] 2.4 `common/ledger.py` に `check_daily_limit(phase)` 実装
  - **docstring に「監視・モニタリング用のみ。本番判定では reserve() を使うこと」を明記**
- [x] 2.5 `common/model_selector.py` 新規作成
  - SPEC §3.3 の挙動表を実装
  - `models.list()` 結果を5分キャッシュ
- [x] 2.6 `models.list()` 失敗時の指数バックオフ(1s, 3s)実装
  - **全失敗時は select_model を中断し reason=error_transient_models_list で返す**(fallback には進めない)
- [x] 2.7 連続3回失敗で LINE 通知昇格(SPEC §12)
- [x] 2.8 `common/ledger.py` に `log_event(reason, detail, phase, block_type, script)` を新規追加(SPEC §11.3、event_log テーブル INSERT、script も記録)

## Phase 3: 装置2 - フェーズ別単発閾値

- [x] 3.1 `cost_guard.py` に `PHASE_THRESHOLD_MAP` 定数追加(.env から動的読み込み)
- [x] 3.2 `estimate_cost(model, in_tokens, out_tokens)` 実装
  - 未登録モデル: **gpt-4o の 1.5倍** fallback rate
- [x] 3.3 `check_phase_threshold(model_class, estimated_cost) -> bool` 実装
- [x] 3.4 override時の class 再判定(SPEC §3.4)

## Phase 4: 装置3 - 重複起票防止(claim方式)

- [x] 4.1 `common/dedup.py` 新規作成
  - `compose_dedup_key(date, block_type, phase, target_id="") -> str`
  - `claim_dedup(dedup_key, ttl_sec=3600) -> str | None`
    - sqlite UNIQUE 制約で INSERT OR FAIL
    - 後着は None を返す → 呼び出し側で reason=skipped_duplicate
  - `release_dedup(claim_id)` 実装(transient失敗時)
  - `confirm_dedup(claim_id, error=False)` 実装(成功/permanent失敗時)
- [x] 4.2 `config/dedup_target_required.json` を読み込んで target_id 必須/任意を判定
  - 必須系で未指定 → **reason=error_missing_target_id**(message="target_id required for block_type=...")
- [x] 4.3 `claim_dedup()` 内で同一トランザクション内 inline purge を実装(TTL実効値化、SPEC §5.3)
- [x] 4.4 週次 cron で `confirmed=1` の履歴を `dedup_claims_archive` へ移動(統計用)（`maintenance/weekly_dedup_archive.py` 作成済み）
- [x] 4.5 TTL 設定可能化(`.env: DEDUP_CLAIM_TTL_SEC`)

## Phase 5: 統一エントリポイント

- [x] 5.1 `cost_guard.py` に `Decision` dataclass 定義(SPEC §7.1、claim_id フィールド含む)
- [x] 5.1b `Decision` の失敗時フィールド既定値(model="" / model_class="" / estimated_cost=0.0 / reservation_id=None / dedup_key="" / claim_id=None)を実装(SPEC §7.1)
- [x] 5.1c `Decision` に `detail: str = ""` / `script: str = ""` フィールド追加(SPEC §7.1)
- [x] 5.1d `Decision` に `phase: str = ""` / `block_type: str = ""` フィールド追加(SPEC §7.1)
- [x] 5.2 `cost_guard.allowed()` 実装(SPEC §6 実行順序 1〜7)
- [x] 5.2b `allowed()` の `model_hint` 引数を実装(存在確認OK→優先採用 / 不在→通常解決フォールバック+警告ログ、SPEC §7.1)
- [x] 5.2c `allowed()` 段階失敗時の `ledger.log_event()` 呼び出しを実装(SPEC §7.3)
- [x] 5.2d `allowed()` シグネチャに `script: str = ""` を追加し、Decision.script に伝搬(SPEC §7.1)
- [x] 5.2e `allowed()` 失敗時の Decision.detail に error_internal 系の切り分け情報を設定(SPEC §7.3.1 表)
- [x] 5.3 `cost_guard.finalize(decision, in_tokens, out_tokens, success, error_kind)` 実装
  - error_kind: "" / "transient" / "permanent_auth" / "permanent_bad_request" / "permanent_response_invalid" / "permanent_api"
  - permanent_* は record + confirm_dedup(error=True)
  - transient は release + release_dedup
  - **不正引数 raise**: success=False かつ error_kind="" / success=True かつ error_kind!="" → raise ValueError(`python -O` 対策で assert 不使用、SPEC §7.1)
  - finalize() 内で `ledger.record(..., script=decision.script)` のように Decision.script を必ず渡す
  - **finalize 全体を 1つの BEGIN IMMEDIATE トランザクションで包み、内部 `_xxx_in_tx` 関数を直列呼び出し**(SPEC §3.2.2)
  - ROLLBACK 時は `ledger.log_event(reason="error_internal", detail="finalize_state_mismatch", phase=..., block_type=..., script=...)` を記録
- [x] 5.4 reason enum を `cost_guard.reasons` に Enum クラスで定義(SPEC §9 **全14値**: error_missing_target_id 追加)
- [x] 5.5 `estimate_cause()` 実装と入出力例追記(SPEC §11.3)
- [x] 5.6 呼び出し側に「try/finally で finalize 必須」のドキュメント整備（`cost_guard.finalize()` docstring にパターン例追記済み）
- [x] 5.7 `finalize()` の冪等性実装(reservation.finalized=1済 or claim確定/解除済 → no-op)
- [x] 5.8 `Decision.reason` 成功時は "ok" 固定で返す

## Phase 6: 通知優先順位

- [x] 6.1 `common/notifier.py` 新規作成
- [x] 6.2 reason → 優先度マップ(SPEC §10、reason enum 13値の対応表)
- [x] 6.3 LINE残通数チェックで降格判定(残10/30 の閾値)
- [x] 6.4 連続3回失敗で `error_transient_*` を優先度3に昇格

## Phase 7: 既存呼び出し側の置換

- [x] 7.1 `gate_checker/gate_check.py` を `cost_guard.allowed()` 経由に置換 + finalize 呼び出し（`agreement_checker.py` の GPT/Sonnet 経路含む）
- [x] 7.2 `matching_v3/skill_judge.py` を `cost_guard.allowed()` 経由に置換 + finalize 呼び出し
- [x] 7.3 `mail_pipeline.py` を `cost_guard.allowed()` 経由に置換 + finalize 呼び出し（legacy `can_spend` 除去済み）
- [x] 7.4 `freee/freee_invoice_v2.py` の LLM 呼び出し箇所を置換（LLM呼び出しなし → 対応不要・docstring確認済み）
- [x] 7.5 `line_webhook/line_bridge.py` の LLM 呼び出し箇所を置換（`guarded_anthropic_call` → allowed/finalize try/finally。Cloud Run再デプロイは Phase 10 で松野確認後）
- [x] 7.6 exit 2 を「スキップして次へ」と扱うラップ関数を共通化(`common/exit_handler.py`)
- [x] 7.7 `matching_v2` を直接呼ぶ箇所を grep で全消去確認

## Phase 8: テスト

- [x] 8.1 test_phase_threshold.py(境界値)
- [x] 8.2 test_dedup_claim.py(claim INSERT)
- [x] 8.3 test_call_limit.py
- [x] 8.4 test_judge_order.py(§6 順序検証)
- [x] 8.5 test_exit_code2.py(誤爆防止)
- [x] 8.6 test_call_limit_race.py(2プロセス並行)
- [x] 8.7 test_dedup_claim_race.py(2プロセス並行 UNIQUE違反)
- [x] 8.8 test_models_list_failure_reason.py(リトライ後 error_transient_models_list)
- [x] 8.9 test_duplicate_does_not_consume_daily_call.py
- [x] 8.10 test_reservation_rollback.py(transient失敗で release)
- [x] 8.11 test_dedup_claim_transient_release.py(transient失敗で release_dedup → 再claim可能)
- [x] 8.13 test_missing_target_id_reason.py(必須系で未指定 → reason=error_missing_target_id)
- [x] 8.13b test_dedup_claim_ttl_inline_purge.py(claim_dedup 内で期限切れ未確定 claim を purge)
- [x] 8.13c test_dedup_claim_expired_reclaim.py(claim → finalize なし → TTL 経過 → 再 claim 成功)
- [x] 8.13d test_finalize_idempotent.py(finalize 2回呼び出しでも safe)
- [x] 8.14 test_finalize_permanent_kinds.py(permanent_auth/bad_request/response_invalid/api)
- [x] 8.15 test_v2_v3_no_mixed_call.py
- [x] 8.17 test_reserved_decrement.py(成功/permanent失敗時 phase_calls.reserved 確実に -1、SPEC §3.2.1)
- [x] 8.18 test_lock_timeout_internal.py(BEGIN IMMEDIATE timeout で reason=error_internal, detail=lock_timeout)
- [x] 8.19 test_finalize_invalid_args.py(success/error_kind 不正組み合わせで `raise ValueError`)
- [x] 8.20 test_model_hint.py(優先採用 / 不在時フォールバック)
- [x] 8.21 test_decision_detail.py(error_internal 時に Decision.detail へ lock_timeout 等が設定される)
- [x] 8.22 test_decision_script.py(allowed→Decision→finalize→ledger.record の script 伝搬)
- [x] 8.23 test_finalize_atomicity.py(finalize 内の中途失敗で全操作が ROLLBACK され、event_log に finalize_state_mismatch が記録される)
- [x] 8.16 全テスト pytest 実行 → 全 PASS

## Phase 9: ゲート②

- [x] 9.1 暫定経路(gpt-5.4 reasoning_effort=low max_completion_tokens=8000)で実装レビュー取得
- [x] 9.2 「条件付きGO」以下なら修正（v2.10.1 patch で NG 修正 → GO）
- [x] 9.3 「GO」確認後 Phase 10 へ（gate2_review_v2.10.1_final.md 参照）

## Phase 10: デプロイ

- [ ] 10.1 既存 cron / Task Scheduler から旧 cost_guard 系を停止
- [ ] 10.2 新 ledger / cost_guard を本番デプロイ
- [ ] 10.3 24時間モニタリング
- [ ] 10.4 SES Knowledge Wiki に「装置1〜3 v2.4 デプロイ完了」追記
- [ ] 10.5 旧 cost_state.json.bak_v2.4 を3ヶ月保持

## 変更履歴

| 日付 | バージョン | 内容 |
|---|---|---|
| 2026-06-16 | v2.0〜v2.2 | (初版〜判定順序統一) |
| 2026-06-16 | v2.3 | sqlite並行制御 / 統一エントリ / 予約方式 |
| 2026-06-16 | v2.4 | claim方式 / reason enum拡張(13値) / models.list 中断統一 / target_id 必須マップ / TTL設定可能化 |
| 2026-06-16 | v2.5 | error_missing_target_id 新設(14値) / TTL inline purge 実装追加 / finalize 冪等性 / Decision.reason "ok" 固定 / 3つの新規テスト追加 |
| 2026-06-16 | v2.6 | (SPEC のみ更新、TASKS への実質変更なし) |
| 2026-06-16 | v2.7 | Phase 8 から test_dedup_ttl_expiry.py 削除(§5.3 inline purge と矛盾)/ 対応SPEC を v2.7 に更新 |
| 2026-06-16 | v2.8 | gate①六反映: Phase 2.3b/2.3c で reserved 減算実装明記 / 2.8 で log_event 追加 / 5.1b で Decision 既定値 / 5.2b で model_hint / 5.2c で log_event 呼び出し / 5.3 で不正引数assert / 1.1 で event_log テーブル(7テーブル化) / Phase 8 にテスト4本追加(8.17〜8.20) |
| 2026-06-16 | v2.9 | gate①七反映: 5.1c で Decision.detail/script / 5.2d で allowed script 伝搬 / 5.2e で detail 設定 / 5.3 不正引数を raise ValueError に / Phase 8 にテスト2本追加(8.21/8.22) |
| 2026-06-16 | v2.10 | gate①八反映: 2.3d で _in_tx 関数群 / 5.1d で Decision.phase/block_type / 5.3 で finalize 単一トランザクション化 + ROLLBACK時 log_event / 2.8 log_event に script / 1.1 event_log に script列 / 8.19 ValueError 修正 / 8.23 test_finalize_atomicity 追加 |
| 2026-06-17 | v2.10 実装 | Phase 0〜8 実装完了。pytest 72テスト全 PASS。本番 sqlite 移行実行(0.5/1.4) |
