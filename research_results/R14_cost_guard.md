# R14: cost_guard_v2 調査
調査日: 2026-06-18

## 結論（1行）
cost_guard_v2（`allowed()`/`finalize()` + SQLite SSoT）は3装置・予約制限・claim dedup・原子finalizeが実装済みで113/116テスト合格；残課題はUTC/JST日付境界の不整合、WAL未設定、legacy `CostGuard` クラス欠落、および調査指示の「装置3=Notion自動起票」と実装（重複起票防止）の定義差。

## 3装置の実装状況
| 装置 | 機能 | 実装状態 | 問題点 |
|---|---|---|---|
| 装置1 | フェーズ別モデル選択 + DAILY_CALL_LIMIT（予約方式）+ グローバル予算 `$8/日・$140/月` | 実装済み（`common/model_selector.py` + `common/ledger.reserve()` + `cost_guard.allowed()` Step 1/6/7） | 日付キーが UTC（ledger）vs JST（Layer2 `get_costs()`）で日次境界がずれる可能性 |
| 装置2 | フェーズ別単発コスト閾値（light `$0.025` / medium `$0.10` / heavy `$0.15`） | 実装済み（`cost_guard._phase_threshold()` → Step 3、超過時 `exit_code=1`） | `.env` の `PHASE_THRESHOLD_*` 未設定時はコード内デフォルト値を使用 |
| 装置3 | 重複起票防止（claim方式 + `target_id` 必須マップ） | 実装済み（`common/dedup.claim_dedup()` + SQLite UNIQUE、`config/dedup_target_required.json`） | 調査指示の「auto Notion ticket creation」とは別物（Notion起票は `tests/test_notion_register.py` 等で独立）；通知は `common/notifier.py`（LINE）のみ |

**補足（2層アーキテクチャ）**

- **Layer1（v2 per-call）**: `cost_guard.allowed()` / `finalize()` — 各 LLM 呼び出し前後
- **Layer2（緊急停止）**: `cost_guard.main()` — `$20/日・$300/月` で Windows タスク停止 + Cloud Run `LLM_KILL=1`

## DAILY_CALL_LIMIT

### 仕様
- デフォルト: `DAILY_CALL_LIMIT_DEFAULT=30`（`.env` / `common/ledger._call_limit()`）
- フェーズ別オーバーライド: `DAILY_CALL_LIMIT_<PHASE>`（例: `DAILY_CALL_LIMIT_IMPLEMENTATION=10`）
- 判定式: `consumed + reserved >= limit` なら予約不可

### reservation-based locking の実装
`common/ledger.reserve(phase)`（`BEGIN IMMEDIATE` 内）:

1. `phase_calls` から `(date, phase)` の `reserved` / `consumed` を読む
2. 在庫があれば `reserved += 1` し `reservations` に UUID 行を INSERT
3. 上限到達なら `None` を返す（ロールバック）

### 予約→消費→解放ライフサイクル

| イベント | `reserved` | `consumed` | `reservations.finalized` |
|---|---|---|---|
| `reserve()` 成功 | +1 | 変化なし | 0 |
| `finalize(success=True)` → `_record_in_tx` | -1（MAX(0)） | +1 | 1 |
| `finalize(transient)` → `_release_in_tx` | -1（MAX(0)） | 変化なし | 1 |
| `allowed()` で budget 超過 cleanup | -1 | 変化なし | 1 |

- **重複呼び出し**（`skipped_duplicate`）: claim が失敗するため `reserve()` まで到達せず、**daily call を消費しない**（`tests/test_duplicate_does_not_consume_daily_call.py` で検証）

### デッドロックの可能性
- SQLite 単一ファイル + 全更新が `BEGIN IMMEDIATE` — 伝統的デッドロック（循環待ち）は**低い**
- 競合時は `OperationalError: database is locked` → `error_internal` / `detail=lock_timeout` / `exit_code=2`（timeout **5秒**、`SQLITE_TIMEOUT_SEC`）
- 予約取得後に後段失敗した場合、claim/reservation の rollback パスが実装済み（budget 超過・lock_timeout 等）
- **リスク**: 5秒 timeout 超過時に呼び出し側が `finalize()` 未実行だと `reserved` が一時的に残る（`finalized=0` の orphan reservation）。TTL による自動回収は未実装

## claim-based deduplication

### 重複検出方法
- `dedup_key = f"{date}:{block_type}:{phase}:{target_id}"`（UTC 日付、`common/dedup.compose_dedup_key()`）
- `claim_dedup()` が `INSERT OR FAIL INTO dedup_claims ... UNIQUE(dedup_key)` — 後着プロセスは `IntegrityError` → `claim_id=None` → `skipped_duplicate` / `exit_code=2`

### タイムウィンドウ
- デフォルト TTL: **3600秒（1時間）**（`.env: DEDUP_CLAIM_TTL_SEC`）
- 同一 `dedup_key` の再実行可否:
  - **confirmed=1, error=0/1**（成功/permanent）: TTL 内はブロック、confirmed レコードは purge しない
  - **confirmed=1, error=2**（transient release）: 即座に DELETE され再 claim 可能
  - **confirmed=0 かつ TTL 超過**: inline purge で DELETE され再 claim 可能

### finalize との連携
- success → `confirm_dedup(error=False)`
- permanent → `confirm_dedup(error=True)`（再試行不可）
- transient → `release_dedup`（`error=2` マーカー、再試行可）

## 並列制御

### 複数プロセス同時アクセス
- DB パス: `%LOCALAPPDATA%/ses_work_state/state.sqlite3`（OneDrive 外、`common/state_store.get_db_path()`）
- 全書き込み: `BEGIN IMMEDIATE` トランザクション（`reserve`, `claim_dedup`, `finalize`, `log_event`）
- レーステスト: `tests/test_call_limit_race.py`, `tests/test_dedup_claim_race.py`

### WALモード / busy_timeout
| 項目 | 実装値 | 備考 |
|---|---|---|
| journal_mode | **delete**（デフォルト） | コード内で `PRAGMA journal_mode=WAL` 未設定 |
| busy_timeout | **5000 ms** | `sqlite3.connect(..., timeout=5)` 経由 |
| ロック戦略 | BEGIN IMMEDIATE のみ | 読み取りは autocommit、書き込みは排他 |

WAL 未使用のため、書き込み競合時は reader/writer 双方がブロックされうる。5秒 timeout で `lock_timeout` に落ちる設計。

## cost_state.jsonとSQLiteの関係

| ストア | パス | 役割 | SSoT |
|---|---|---|---|
| SQLite `state.sqlite3` | `C:\Users\ma_py\AppData\Local\ses_work_state\state.sqlite3` | daily/monthly USD、phase_calls、reservations、dedup_claims、event_log | **正（v2.4 以降）** |
| `cost_state.json` | 同上ディレクトリ | v2.4 移行前の JSON ledger | **移行済み** → `cost_state.json.bak_v2.4`（2026-06-16 時点: daily=$0.03, monthly=$6.22） |
| `cost_guard_state.json` | OneDrive `ses_work/cost_guard_state.json` | Layer2 緊急停止フラグ（`stopped_today` 等） | Layer2 専用（コスト累計とは別） |
| `usage_tracker/cost_log.jsonl` | OneDrive 配下 | 監査用 append-only ログ | 参照用；ledger 読み取りエラー時は `can_spend` が True を返す（フェイルオープン） |

### 更新タイミング
- **SQLite**: `finalize()` 成功/permanent 時の `_record_in_tx()` で `daily_state` / `monthly_state` UPSERT
- **cost_log.jsonl**: `ledger.record()` / blocked 時の `_append_log()` で追記
- **cost_state.json**: 現行コードからは**書き込みなし**（`migrate_to_sqlite_v2.4.py` で一回移行のみ）

### 不整合リスク
1. **`cost_guard.get_costs()` の stale コメント** — 「cost_state.json を正とし」と記載あるが、実際は `ledger.daily_total()` / `monthly_total()`（SQLite）を `max()` 合成
2. **UTC vs JST** — ledger の date/month キーは UTC、Layer2 の cost_log 集計は JST 00:00。JST 09:00 前後で日次境界が Layer1/Layer2 で不一致になりうる
3. **`can_spend` 読み取りエラー時 True** — DB 破損/ロック時に予算ガードがスキップされる（意図的フェイルオープン）
4. **orphan reservation** — finalize 未到達 + lock_timeout 時に `reserved` が残存しうる

## 月次管理

### リセットタイミング
- **明示的リセット処理なし** — キー切り替え方式
- `monthly_state`: `_now_month()`（UTC `YYYY-MM`）が変わると新行 INSERT、旧月データは残存
- `phase_calls` / `daily_state`: UTC 日付キーで日次自動切替
- Layer2 `cost_guard_state.json`: `reset_state_if_needed()` で JST 日付/月変更時に `stopped_today` / `stopped_monthly` フラグをリセット

### リセット中の保護
- 月跨ぎ瞬間: 新 `month` キーは `monthly_usd=0` から開始 → 一時的に予算に余裕ができる（意図通り）
- 同時 API 呼び出し: `BEGIN IMMEDIATE` で serialize — リセット「処理中」という特殊状態はなく、新旧 month キーへの INSERT/UPDATE が競合するだけ
- **注意**: UTC 月初 00:00 と JST 月初 00:00 が9時間ずれる

## テスト結果

```
pytest tests/ -q  →  113 passed, 3 failed, 2 warnings（実行日: 2026-06-18）
```

| 区分 | 件数 | 内容 |
|---|---|---|
| cost_guard コア（dedup/reserve/finalize/exit_code 等） | **113 合格** | `tests/test_*` のうち cost_guard 関連は全 PASS |
| 失敗 3件 | `tests/test_mail_pipeline_bc.py` | cost_guard 無関係（削除済み関数 `_parse_imap_internaldate`, `notion_register_engineer`, `maybe_save_processed_id` 参照） |
| 警告 2件 | race テスト | `@pytest.mark.timeout` 未登録 |

**116テスト**: `tests/` ディレクトリ合計 116 件。指示書の「116 passing」は mail_pipeline_bc 3件を除く **113/113 cost_guard 関連 PASS** と解釈するのが正確。

### 主要テストファイル（cost_guard v2）
- `test_call_limit.py`, `test_call_limit_race.py` — DAILY_CALL_LIMIT 予約
- `test_dedup_claim*.py` — claim/TTL/race/transient
- `test_finalize_*.py` — 原子性・冪等・state_mismatch
- `test_exit_code2.py`, `test_judge_order.py`, `test_phase_threshold.py`
- `test_duplicate_does_not_consume_daily_call.py`

## exit code 2（cost/rate limit skip）の使われ方

### SPEC 定義（`cost_guard.Reasons` + `Decision.exit_code`）

| exit_code | reason 例 | 意味 | 呼び出し側の期待動作 |
|---|---|---|---|
| **0** | `ok` | 許可 | LLM 実行 → `finalize()` |
| **1** | `stopped_budget`, `stopped_call_limit`, `stopped_phase_threshold` | 停止（当日/入力変更まで不可） | スキップまたはエラー扱い |
| **2** | `skipped_duplicate`, `error_transient_*`, `error_*`, `error_internal` | スキップ（リトライ可/不要） | **正常スキップ**として処理継続 |

### 実装箇所
- `cost_guard.allowed()` — 各 Step の失敗時に `Decision.exit_code` を設定
- `common/exit_handler.ExitCode2` — exit 2 を例外として伝播
- `matching_v3/skill_judge.py`:
  - `exit_code == 2` → `raise ExitCode2`（スキップ）
  - `exit_code == 1` → `raise RuntimeError`（ブロック）
- `common/exit_handler.run_with_skip()` — `ExitCode2` / `SystemExit(2)` をキャッチして `None` 返却

### LLM_KILL=1
- Layer2 `cost_guard.main()` が `$20/日` or `$300/月` 到達時に Cloud Run env + Windows タスク DISABLE
- per-call の exit code 2 とは別系統（インフラレベル即時停止）

## 推奨アクション
- [ ] **UTC/JST 日付キー統一** — `ledger._now_date()` / `_now_month()` を JST に揃えるか、SPEC に UTC 運用を明記
- [ ] **SQLite WAL 有効化検討** — `init_schema()` 後に `PRAGMA journal_mode=WAL` + reader 競合低減
- [ ] **orphan reservation 回収** — `finalized=0` かつ `created_at` 超過分を定期 purge（または stale reservation TTL）
- [ ] **legacy `CostGuard` 整理** — ルート `cost_guard.py` から `CostGuard` クラスが削除済みだが `matching_v3/matching_v3.py` が `from cost_guard import CostGuard` を参照（import 失敗リスク）。`matching_v3/cost_guard.py` への import 修正または re-export
- [ ] **stale コメント修正** — `cost_guard.get_costs()` L165「cost_state.json を正とし」→ SQLite ledger に更新
- [ ] **`test_mail_pipeline_bc.py` 3件修正** — 116/116 PASS を回復（cost_guard とは独立）
- [ ] **憲法/ドキュメント更新** — `ジョブズ行動憲法v1.md` の「cost_state.json 正本」記述を SQLite SSoT に更新
