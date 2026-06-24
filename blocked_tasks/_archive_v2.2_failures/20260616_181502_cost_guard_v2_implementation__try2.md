# 【Cursor作業指示】cost_guard_v2 実装 (SPEC v2.10 GO判定済み)

対象ディレクトリ:
- `ses_work/cost_guard_v2/` (SPEC/TASKS/CLAUDE)
- `ses_work/common/` (ledger.py + 新規 state_store/model_selector/dedup/notifier/exit_handler)
- `ses_work/cost_guard.py` (改修)
- `ses_work/matching_v3/skill_judge.py` (改修)
- `ses_work/migrations/migrate_to_sqlite_v2.4.py` (新規)
- `ses_work/config/dedup_target_required.json` (新規)

---

## 前提

- SPEC v2.10 / TASKS v2.10 / CLAUDE v2.10 でゲート① 8回反復(v2.2 → v2.10)の結果、**GO 判定取得済み**
- 必須項目 0、推奨3項目のみ(実装中対応で十分、後述)
- `cost_guard_v2/gate1_review_v2.10.md` で GPT-5.4 が「実装不能な矛盾は見当たりません」「`Decision.phase` / `Decision.block_type` / `script` / `detail` の追加により障害解析文脈も実用上十分」「既存呼び出し側との互換性も致命的不整合は見当たりません」と確認

---

## 必須参照ファイル(必ず最初に読む順序)

1. **`ses_work/cost_guard_v2/CLAUDE.md`** (作業ルール、禁止事項、reason enum 14値)
2. **`ses_work/cost_guard_v2/SPEC.md`** (仕様。特に重要な節:
   - §3.2.1: 予約方式と reserved 減算の3パターン
   - §3.2.2: **finalize 原子性(単一 BEGIN IMMEDIATE で 6 操作を原子的実行、public/_in_tx 分離)**
   - §5.3: claim TTL inline purge
   - §6: 統一実行順序(1〜7)
   - §7.1: allowed/finalize シグネチャと Decision dataclass(detail/script/phase/block_type 含む)
   - §7.3 / §7.3.1: allowed() 段階失敗の event_log 記録タイミング(8段階)
   - §8.2: sqlite 7テーブル設計
   - §11: ledger.py 拡張仕様)
3. **`ses_work/cost_guard_v2/TASKS.md`** (実装チェックリスト Phase 0〜10)

---

## 作業内容

SPEC v2.10 / TASKS v2.10 に従って **装置1〜3 + DAILY_CALL_LIMIT(事前予約) + 重複起票防止(claim方式) + sqlite並行制御(BEGIN IMMEDIATE)** を実装。

### 実装方針(SPEC v2.10 のキー設計)

- 既存 `common/ledger.py` の関数シグネチャは温存(can_spend/record/daily_total/monthly_total、後方互換)
- `record()` は kwargs 拡張(phase/reservation_id/fallback/unknown_model/error/reason/detail、SPEC §11.2)
- 新規関数群: reserve / release / claim_dedup / release_dedup / confirm_dedup / check_daily_limit / log_event / estimate_cause
- **public エントリと内部 `_xxx_in_tx(conn, ...)` を分離**(SPEC §3.2.2、record/release/confirm_dedup/release_dedup の4関数)
- **finalize() は単一 BEGIN IMMEDIATE トランザクション**で内部 `_xxx_in_tx` を直列呼び出し → 1回 COMMIT
- sqlite3 経路に統一(`state.sqlite3`、`STATE_DIR=%LOCALAPPDATA%\\ses_work_state`、§13)
- 既存 `cost_state.json` から `migrations/migrate_to_sqlite_v2.4.py` で1回移行
- 不正引数は **`raise ValueError`** で拒否(assert は `python -O` で無効化されるため使わない、SPEC §7.1)
- `Decision.script` は allowed() に渡された値を保持 → finalize() で ledger.record(... script=...) に伝搬

---

## 完了条件

- TASKS.md の **Phase 0〜8(実装 + テスト)を完了**
- pytest 全テスト PASS(23本: Phase 8.1〜8.23)
- 主要テスト:
  - test_finalize_atomicity.py(finalize 内 ROLLBACK 検証)
  - test_finalize_invalid_args.py(**`raise ValueError`** 検証、AssertionError ではない)
  - test_reserved_decrement.py(成功/permanent失敗で reserved -=1)
  - test_dedup_claim_ttl_inline_purge.py / test_dedup_claim_expired_reclaim.py
  - test_decision_detail.py / test_decision_script.py
  - test_call_limit_race.py / test_dedup_claim_race.py(並行系)
- **Phase 9(ゲート②)以降はジョブズ(Claude.ai)が担当**

---

## 進め方

1. Phase 0(準備)→ Phase 1(並行制御 sqlite、最優先) を必ず先に
2. 各 Phase 完了ごとに TASKS.md のチェックボックスを更新
3. 同じエラーで 2 回失敗 → `wall_hitting.py --problem "<内容>"` で壁打ち
4. 仕様判断不能 → Claude.ai ジョブズに質問(質問ファイルを `pending_tasks/_question/YYYYMMDD_HHMMSS_<topic>.md` に作成)
5. 完了 → 報告ファイル `pending_tasks/_done/20260616_181502_cost_guard_v2_done.md` を作成(完了 Phase 一覧 + テスト結果 + 残課題)

---

## 推奨3項目(v2.10 ゲート①の推奨、実装中対応で十分)

1. **finalize() の冪等 no-op 条件**: `reservation.finalized=1` と `claim 確定/解除済み` の片側だけが成立した場合の挙動をコードコメントで明示(DB手修正・旧コード混在・障害復旧時の切り分け用)
2. **ROLLBACK 時の log_event**: `finalize` 内の ROLLBACK 時、`log_event(reason="error_internal", detail="finalize_state_mismatch")` は **rollback 後に別トランザクションで best-effort 記録**(同一 conn 再利用で OK)
3. **SPEC §3.2.2 の節番号採番整理**: 文書保守上の推奨。実装には影響しない

---

## 注意事項(CLAUDE.md §2 禁止事項より)

- **CostGuard なしの LLM 呼び出し禁止**: 全 LLM 経路で `cost_guard.allowed()` を通す、`finalize()` を try/finally で必ず呼ぶ
- 装置3 重複時は **完全スキップ + claim方式**(counter 追記しない、事後 mark もしない)
- 判定順序: SPEC §6 通り(逆順禁止)
- finalize() の record/release/confirm_dedup/release_dedup は **必ず単一トランザクション**で実行(別々の BEGIN IMMEDIATE 禁止、SPEC §3.2.2)
- `ledger.record()` を `script=""` で呼ばない(Decision.script を必ず伝搬)
- `models.list()` 全失敗時に fallback を試みる旧実装禁止(中断して `error_transient_models_list`、SPEC §3.3 / §12)
- 文字エンコーディング: UTF-8固定。`common/io_utils.py` の `setup_stdout()` を使う(pythonw対策の try/except 込み)
- 日本語パスを cwd/コマンドに直接渡さない

---

## 質問がある場合

Claude.ai チャットに該当箇所を貼って確認。質問ファイル: `pending_tasks/_question/YYYYMMDD_HHMMSS_<topic>.md`


## RETRY 1 REASON
target_file not found: 


## RETRY 2 REASON
target_file not found: 


## BLOCKED REASON
target_file not found: 
