# 【Claude Code 即時実装指示】cost_guard_v2 (SPEC v2.10 GO判定済み)

---

## 🚨 厳守ルール(最優先・違反不可)

- **最初の応答は自然言語の説明ではなく、ツール実行(Read など)から開始する。**
- **3つの必須参照ファイル(下記)を読了した次の操作で、必ず1件以上のファイル作成または編集を実行する。**
- **計画・確認・質問のみを出力して終了することは禁止。少なくとも1ファイルを変更するまで終了してはならない。**
- **承認・確認・「以下の計画でよろしいですか」のような発話は禁止。事前承認済み。**
- **不明点があっても、依存しない箇所は先に実装する。質問ファイル作成は実装継続が完全に不可能な場合に限る。**
- **全実装・必要テスト完了時のみ最後に `IMPL_COMPLETE` を出力する。未完了時は出力しない。**
- **ses_work ディレクトリ外への書き込み禁止。**

---

## 前提

- SPEC v2.10 / TASKS v2.10 / CLAUDE v2.10 でゲート① 8回反復(v2.2 → v2.10)の結果、**GO 判定取得済み**
- 必須項目 0、推奨3項目のみ
- `cost_guard_v2/gate1_review_v2.10.md` で GPT-5.4 が「実装不能な矛盾は見当たりません」と確認済み
- CEO 松野とジョブズで事前承認済み。直ちに実装開始すること

---

## 必須参照ファイル(この順で Read、その後すぐに最初のファイル作成へ)

1. `ses_work/cost_guard_v2/CLAUDE.md`
2. `ses_work/cost_guard_v2/SPEC.md`
3. `ses_work/cost_guard_v2/TASKS.md`

**読了後の最初の書き込み対象は `ses_work/config/dedup_target_required.json`** とする(SPEC §5.4)。これを作成してから他のファイルへ進む。

---

## 対象ディレクトリ・ファイル

- `ses_work/config/dedup_target_required.json` (新規、最初の作成対象)
- `ses_work/common/state_store.py` (新規、sqlite3 接続管理、§8.2 の 7テーブル init_schema)
- `ses_work/common/model_selector.py` (新規)
- `ses_work/common/dedup.py` (新規、claim方式)
- `ses_work/common/notifier.py` (新規)
- `ses_work/common/exit_handler.py` (新規)
- `ses_work/common/ledger.py` (改修、既存シグネチャ温存 + kwargs 拡張 + 新関数追加)
- `ses_work/cost_guard.py` (改修、統一エントリ allowed/finalize 新設)
- `ses_work/matching_v3/skill_judge.py` (改修)
- `ses_work/migrations/migrate_to_sqlite_v2.4.py` (新規)
- `ses_work/tests/` (テスト 23本、Phase 8.1〜8.23)
- `ses_work/config/.env` (新規定数追加、**Phase 0 の最後に対応**)

---

## 実装方針(SPEC v2.10 のキー設計)

- 既存 `common/ledger.py` の関数シグネチャは温存(can_spend/record/daily_total/monthly_total、後方互換)
- `record()` は kwargs 拡張(phase/reservation_id/fallback/unknown_model/error/reason/detail、SPEC §11.2)
- 新規関数: reserve / release / claim_dedup / release_dedup / confirm_dedup / check_daily_limit / log_event / estimate_cause
- **public エントリと内部 `_xxx_in_tx(conn, ...)` を分離**(SPEC §3.2.2、record/release/confirm_dedup/release_dedup の4関数)
- **finalize() は単一 BEGIN IMMEDIATE トランザクション**で内部 `_xxx_in_tx` を直列呼び出し
- sqlite3 経路に統一(`state.sqlite3`、`STATE_DIR=%LOCALAPPDATA%\\ses_work_state`、§13)
- 不正引数は **`raise ValueError`**(assert は `python -O` で消えるので不使用)

---

## 進め方(コード実装を最優先、TASKS.md チェック更新は関連実装後でよい)

1. **Read** で CLAUDE.md / SPEC.md / TASKS.md を順に読む
2. **次のターンで即座に** `config/dedup_target_required.json` を新規作成
3. 続けて Phase 1(`common/state_store.py`、sqlite 7テーブルの init_schema)
4. Phase 2(装置1 ledger.py 拡張、`model_selector.py`)
5. Phase 3(装置2 cost_guard.py の閾値判定)
6. Phase 4(装置3 `common/dedup.py` claim方式)
7. Phase 5(統一エントリ `cost_guard.allowed()` / `finalize()` の新設)
8. Phase 6(`common/notifier.py`)
9. Phase 7(既存呼び出し側 matching_v3/skill_judge.py 等の置換)
10. Phase 8(テスト23本実装 + pytest 全 PASS)
11. 関連実装が完了したら TASKS.md のチェックボックスを `[ ]` → `[x]` に更新
12. **同じエラーで 2 回失敗した時のみ** 質問ファイル `pending_tasks/_question/YYYYMMDD_HHMMSS_<topic>.md` を作成して終了
13. Phase 8 まで完了して全テスト PASS → 最後に `IMPL_COMPLETE` を出力

---

## 完了条件

- TASKS.md の Phase 0〜8 が完了(チェックボックス更新)
- pytest 全テスト PASS(23本)
- 最後に `IMPL_COMPLETE` 出力

---

## 注意事項

- **CostGuard なしの LLM 呼び出し禁止**(全 LLM 経路で `cost_guard.allowed()` を通す、`finalize()` を try/finally で必ず呼ぶ)
- 装置3 重複時は **完全スキップ + claim方式**(counter 追記しない、事後 mark もしない)
- 判定順序: SPEC §6 通り(逆順禁止)
- finalize() の record/release/confirm_dedup/release_dedup は **必ず単一 BEGIN IMMEDIATE トランザクション**で実行
- `ledger.record()` を `script=""` で呼ばない(Decision.script を必ず伝搬)
- `models.list()` 全失敗時に fallback を試みる旧実装禁止(中断して `error_transient_models_list`、SPEC §3.3 / §12)
- 文字エンコーディング: UTF-8固定、`common/io_utils.py` の `setup_stdout()` を使う(pythonw対策の try/except 込み)
- 日本語パスを cwd/コマンドに直接渡さない


## RETRY 1 REASON
target_file not found: 
