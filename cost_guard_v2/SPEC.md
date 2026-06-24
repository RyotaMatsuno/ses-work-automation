# SPEC.md - cost_guard_v2 仕様書

最終更新: 2026-06-16 / バージョン: v2.10
設計: ジョブズ / レビュー予定: gpt-5.4 (reasoning_effort=low)

---

## 0. 背景

### 0.1 過去の事故
- 2026-06-02: 1日 $50.88 消費、Anthropic アカウント上限到達
- 既知バグ(2026-06-15時点): matching_v2/skill_judge.py が ledger Layer1 バイパス / mail_pipeline が v2 を呼び続け JSONDecodeError 黙殺 / .env 変数名不整合

### 0.2 v2.9→v2.10 で反映した GPT-5.4 ゲート①再指摘
1. §14 `test_finalize_invalid_args.py` の期待例外を `AssertionError` → `ValueError` に修正(v2.9 の raise ValueError 化と整合)
2. §3.2.2 新設: **finalize の原子性** を明文化(record/release/confirm_dedup/release_dedup を単一 BEGIN IMMEDIATE トランザクションで原子的実行、内部 `_xxx_in_tx` 関数化方針も明示)
3. §7.1 Decision に `phase: str = ""` / `block_type: str = ""` フィールド追加(障害解析・finalize_state_mismatch 通知時の文脈確保)
4. §8.2 event_log テーブルに `script TEXT NOT NULL DEFAULT ''` 列追加(allowed() 段階失敗の追跡粒度を finalize 経路と揃える)
5. §9 error_internal の detail 推奨値に `finalize_state_mismatch` を追加

### 0.3 v2.8→v2.9 で反映した GPT-5.4 ゲート①再指摘
1. §7.1 Decision に `detail: str = ""` フィールド追加(error_internal 時の切り分け情報を呼び出し側へ返す)
2. §7.1 Decision に `script: str = ""` フィールド追加 + allowed() シグネチャに `script: str = ""` 引数追加(finalize() が ledger.record() の必須引数 `script` を呼べないという致命的不整合を解消)
3. §7.1 allowed() docstring の「失敗時 Decision 各フィールド既定値」に detail/script を追記
4. §7.1 finalize() の不正引数チェックを assert から `raise ValueError` に変更(`python -O` 最適化実行で assert が無効化される運用リスク回避)
5. §7.3 に「allowed() 段階失敗時の log_event 呼び出しタイミング表」(8段階)を追加して実装漏れ防止
6. §14 にテスト2本追加: test_decision_detail / test_decision_script

### 0.4 v2.7→v2.8 で反映した GPT-5.4 ゲート①再指摘
1. §3.2.1 に予約確定時の `phase_calls.reserved -= 1` を明記(成功/permanent失敗/transient失敗いずれも `reserved -= 1`、`reservations.finalized=1` のセット時点も追記)
2. §7.1 allowed() docstring に「失敗時の Decision 各フィールド既定値」を本文として明記
3. §7.1 finalize() docstring に「不正引数組み合わせ」(success=False かつ error_kind=""、success=True かつ error_kind!="") 時の挙動を明記
4. §7.3 新設: allowed() 段階失敗(record前で終わるケース)の障害イベント記録先を明確化
5. §7.1 allowed() に `model_hint` の仕様(存在すれば優先採用、不在なら phase→model 通常解決にフォールバック)を明記
6. §11.3 ledger.log_event() を新規追加(allowed 段階失敗の記録用)
7. §14 テスト計画に 4本追加: test_reserved_decrement / test_lock_timeout_internal / test_finalize_invalid_args / test_model_hint

### 0.5 v2.6→v2.7 で反映した GPT-5.4 ゲート①再指摘
1. §14 のテスト計画から `test_dedup_ttl_expiry.py(TTL超過分が archive に移動)` を削除(§5.3 inline purge 仕様と矛盾するため、既存の `test_dedup_claim_ttl_inline_purge.py` と `test_dedup_claim_expired_reclaim.py` で代替済み)
2. §5.3 の「再claimレコード側に履歴が残る」言い回しを「未確定期限切れclaimは監査保管せず削除し、再claim後の新レコードのみ現行テーブルに残る」に補正
3. §7.1 allowed()/finalize() の docstring に「成功時 Decision.reason="ok" 固定」「error_kind → reason enum 対応表」を本文として明記
4. §9 error_internal の detail 推奨値例を列挙(lock_timeout / sqlite_corrupt / schema_mismatch / migration_not_run)
5. §11.3 ledger.record() の引数 reason/detail を入出力例で明確化(v2.6で追加した引数の使い方を明文化)

### 0.6 v2.5→v2.6 で反映した GPT-5.4 ゲート①再指摘
1. §5.3 の本文を inline purge 前提の実効TTL 仕様に完全書き換え(v2.5 では §0.2/§14 と §5.3 が衝突していた)
2. `claim_dedup()` の purge 条件 SQL を明文化(`confirmed=0 AND first_seen <= now - ttl_sec`)
3. archive テーブルへ移す条件を明文化(`confirmed=1` のみ)
4. `Decision.reason` 成功時 "ok" 固定を §7.1 docstring に直接追記
5. `error_internal.detail` の格納先を ledger.record の引数で固定

### 0.7 v2.4→v2.5 で反映した GPT-5.4 ゲート①再指摘
1. target_id 必須違反を error_internal から分離し `error_missing_target_id` を新設
2. dedup claim TTL を実効値化: `claim_dedup()` 実行時にトランザクション内で期限切れ未確定claimをinline purge
3. `Decision.reason` 成功時は "ok" 固定を明示
4. `finalize()` の冪等性を明示(reservation.finalized=1済 or claim確定/解除済 → no-op)
5. `error_internal` に `detail` 補助フィールド追加(切り分け迅速化)

### 0.8 v2.3→v2.4 で反映した GPT-5.4 ゲート①再指摘
1. dedup を「事後 mark」→「**事前 claim**」方式に変更(並行実行時の二重実行を sqlite UNIQUE制約で防止)
2. permanent 失敗の reason enum を細分化(error_permanent_api / error_auth / error_bad_request / error_response_invalid)
3. models.list() 全失敗時の挙動を「即時 error_transient_models_list で終了」に統一(§3.3 と §12 の二重定義解消)
4. target_id 必須/任意を block_type ごとに宣言式で管理
5. STATE_DIR 一本化、phase_calls と daily_calls の関係注記、check_daily_limit() の用途制限明記

## 1. Week1 スコープ

| # | 機能 |
|---|---|
| 1 | 装置1: フェーズ別モデル選択 + DAILY_CALL_LIMIT(事前予約方式) |
| 2 | 装置2: フェーズ別単発閾値 |
| 3 | 装置3: 重複起票防止(**claim方式** + target_id 必須マップ) |
| 4 | 並行制御(sqlite3 への移行) |
| 5 | 統一エントリポイント `cost_guard.allowed()` / `cost_guard.finalize()` |
| 6 | reason enum + 通知優先順位対応表 |
| 7 | 既存 exit code 2 互換性 |

## 2. Week2 以降に先送り
- 110解放 / risk_score / 二次壁打ち拡張
- gate_checker 本体バグ修正(別タスク化済み)
- cost_guard.py の OneDrive 配下ハードコード退治(別タスク化)

## 3. 装置1: フェーズ別モデル選択 + DAILY_CALL_LIMIT

### 3.1 フェーズ → モデル対応表

| フェーズ | クラス | 推奨モデル |
|---|---|---|
| research / requirements / test | 軽 | gpt-4o-mini |
| design / pre_impl | 中 | gpt-5.4 |
| implementation | 重 | codex-5 |

### 3.2 DAILY_CALL_LIMIT(事前予約方式)

#### 3.2.1 カウント更新タイミング
```
1. reserve(phase) → reservation_id 発行 + phase_calls.reserved を +1(BEGIN IMMEDIATEトランザクション内)
2. 実LLM呼び出し
3. finalize 時の状態遷移(全て BEGIN IMMEDIATE トランザクション内、原子的):
   - 成功:
       record(..., reservation_id=...)
       → phase_calls.reserved -= 1, phase_calls.consumed += 1
       → reservations.finalized = 1
   - transient失敗(再試行可能):
       release(reservation_id)
       → phase_calls.reserved -= 1(consumed は加算しない)
       → reservations.finalized = 1
   - permanent失敗(再試行不可、エラー記録):
       record(..., reservation_id=..., error=True)
       → phase_calls.reserved -= 1, phase_calls.consumed += 1
       → reservations.finalized = 1

判定式:
  在庫数 = phase_calls.consumed + phase_calls.reserved
  reserve(phase) は 在庫数 >= DAILY_CALL_LIMIT_<phase> のとき None を返す
  (consumed と reserved を合算判定することで予約リーク/誤停止を防ぐ)
```

#### 3.2.2 デフォルト値
- `DAILY_CALL_LIMIT_DEFAULT=30`
- `DAILY_CALL_LIMIT_<PHASE>` で個別オーバーライド可
- 例: `DAILY_CALL_LIMIT_IMPLEMENTATION=10`

### 3.2.2 finalize の原子性(v2.10 で明文化)

finalize() が success/transient/permanent いずれの分岐でも、以下4種の更新を**単一 BEGIN IMMEDIATE トランザクション内で原子的に実行**する:

| 操作 | success | transient | permanent |
|---|---|---|---|
| `phase_calls.reserved -= 1` | ○ | ○ | ○ |
| `phase_calls.consumed += 1` | ○ | × | ○ |
| `reservations.finalized = 1` | ○ | ○ | ○ |
| ledger 行 INSERT(usd/tokens 記録) | ○ | × | ○(error=1) |
| `dedup_claims.confirmed = 1`(error=0/1) | ○ | × | ○ |
| `dedup_claims` 該当行 DELETE(release_dedup) | × | ○ | × |

中途半端な状態(record 完了 + confirm_dedup 前にプロセス断 等)を防ぐため、上記6操作を1つのトランザクションでコミット。失敗時は ROLLBACK で全操作を取り消す。

#### 実装方針(public/_in_tx 分離)

- 各 ledger 関数は public エントリと内部 `_in_tx` 版を持つ:
  - `ledger.record()` ↔ `ledger._record_in_tx(conn, ...)`
  - `ledger.release()` ↔ `ledger._release_in_tx(conn, ...)`
  - `ledger.confirm_dedup()` ↔ `ledger._confirm_dedup_in_tx(conn, ...)`
  - `ledger.release_dedup()` ↔ `ledger._release_dedup_in_tx(conn, ...)`
- public エントリは単独使用時のみ自前で BEGIN IMMEDIATE/COMMIT を実行(既存呼び出し互換性維持)
- finalize() は外側で 1 つの BEGIN IMMEDIATE を取り、内部 `_xxx_in_tx` 関数を直列呼び出し → 1回の COMMIT
- 内部関数間で別トランザクションを開始しないこと(deadlock 回避)
- ROLLBACK 時は `ledger.log_event(reason="error_internal", detail="finalize_state_mismatch", phase=..., block_type=..., script=...)` で記録

### 3.3 モデル不在時の挙動(v2.4で統一)

| 状況 | 挙動 |
|---|---|
| `models.list()` 成功 + 指定モデル存在 | そのまま実行 |
| `models.list()` 成功 + 指定モデル不在 | 同クラス内代替へ fallback(警告ログ + ledger に fallback=True) |
| `models.list()` 失敗(タイムアウト/API エラー) | §12 のリトライ仕様で2回までリトライ |
| `models.list()` 全失敗 | **select_model を中断、即 exit 2 reason=error_transient_models_list**(fallback 経路には進めない) |
| 同クラス代替先も不在 | exit 2 reason=error_model_unavailable_all_fallback |

### 3.4 override 時の class 再判定
- フォールバック先が別クラスでも、装置2の閾値判定は**呼び出し時に指定された phase のクラス**を採用

## 4. 装置2: フェーズ別単発コスト閾値

| クラス | 単発閾値 |
|---|---|
| 軽 | $0.025 |
| 中 | $0.10 |
| 重 | $0.15 |

### 4.1 未知モデル
- レート表(`config/model_rates.json`)未登録 → fallback rate = gpt-4o の **1.5倍**(保守的)
- 警告ログ + ledger に `unknown_model=True` 記録

### 4.2 超過時
- exit 1 reason=stopped_phase_threshold

## 5. 装置3: 重複起票防止(claim方式)

### 5.1 dedup_key 仕様
- `dedup_key = f"{date}:{block_type}:{phase}:{target_id}"`
- target_id 例: 案件ID / メールID / SPECファイルパスSHA / コミットSHA

### 5.2 claim 方式(v2.4の本質変更)

```python
# 旧(v2.3): 事後 mark
is_duplicate(key)  # チェック
do_llm_call()      # 並行プロセスがここで同時通過し二重実行
mark(key)          # 事後マーク

# 新(v2.4): 事前 claim
claim_id = claim_dedup(dedup_key, ttl_sec=3600)
   # sqlite UNIQUE 制約で INSERT。後着は claim_id=None → exit 2 reason=skipped_duplicate
do_llm_call()
finalize(claim_id, success, error_kind)
   # success → confirm_dedup(claim_id, error=False)
   # permanent失敗 → confirm_dedup(claim_id, error=True)  # 再試行不要
   # transient失敗 → release_dedup(claim_id)              # 再試行可能、TTL内なら他プロセスも待機
```

### 5.3 claim TTL(v2.5/v2.6 で実効値化)

- デフォルト: 3600秒(1時間)
- `.env: DEDUP_CLAIM_TTL_SEC` で変更可
- **TTL は実効値**: `claim_dedup()` は同一トランザクション内で以下を順に実行する:
  1. 期限切れ未確定 claim の inline purge
     ```sql
     DELETE FROM dedup_claims
     WHERE confirmed = 0
       AND first_seen <= datetime('now', '-' || ttl_sec || ' seconds');
     ```
     → confirmed=1 のレコードは絶対に回収しない(履歴保護)
  2. 新規 claim の INSERT
     ```sql
     INSERT OR FAIL INTO dedup_claims(claim_id, dedup_key, first_seen, ttl_sec)
     VALUES (?, ?, datetime('now'), ?);
     ```
     → UNIQUE 違反なら None を返す → 呼び出し側は exit 2 reason=skipped_duplicate
- **したがって TTL 経過後は週次cronを待たず即座に再claim可能**
- 週次cron は別用途(監査・統計):
  - `confirmed=1` のレコードを `dedup_claims_archive` へ移動(履歴保管)
  - inline purge で削除済みの未確定レコードは archive 対象外(設計上、未確定期限切れclaimは監査保管せず削除し、再claim後の新レコードのみ現行テーブルに残る)
- **再実行可否の真実源**: `dedup_claims` テーブル本体(archive は監査用)

### 5.4 target_id 必須/任意マップ(v2.4新規)
- `config/dedup_target_required.json` で block_type ごとに宣言:
```json
{
  "gate_check": {"target_id": "required", "format": "spec_file_sha256"},
  "skill_judge": {"target_id": "required", "format": "project_id"},
  "mail_classify": {"target_id": "required", "format": "message_id"},
  "wall_hitting": {"target_id": "optional", "format": "free_text_first_50_chars"},
  "manual_query": {"target_id": "optional", "format": "any"}
}
```
- 必須系で target_id 未指定 → **exit 2 reason=error_missing_target_id**(message=`target_id required for block_type=...`)
- 任意系で未指定 → 空文字フォールバック(従来通り粗粒度)

### 5.5 ストレージ
- §8 sqlite テーブル `dedup_claims` に統合
- UNIQUE 制約: `(dedup_key)`
- archive テーブル: `dedup_claims_archive`(7日経過分を週次移動)

## 6. 統一実行順序(claim方式対応)

```
1. select_model(phase) → (model, model_class)
   ※ models.list() 全失敗時は即 exit 2 reason=error_transient_models_list
2. estimate_cost(model, est_in, est_out)
3. check_phase_threshold(model_class, estimated_cost)
   → 超過なら exit 1 reason=stopped_phase_threshold
4. dedup_key = compose_dedup_key(date, block_type, phase, target_id)
   → block_type が target_id 必須なのに target_id 未指定なら exit 2 reason=error_missing_target_id
5. claim_id = claim_dedup(dedup_key, ttl_sec)
   → None(UNIQUE違反) なら exit 2 reason=skipped_duplicate
6. reservation_id = reserve(phase)
   → None なら release_dedup(claim_id) + exit 1 reason=stopped_call_limit
7. can_spend(est_in, est_out, model)
   → False なら release(reservation_id) + release_dedup(claim_id) + exit 1 reason=stopped_budget
8. 実LLM呼び出し(呼び出し側責務)
   - 成功 → finalize(decision, success=True): record + confirm_dedup
   - transient失敗 → finalize(decision, success=False, error_kind="transient"): release + release_dedup
   - permanent失敗 → finalize(decision, success=False, error_kind="permanent_auth"|"permanent_bad_request"|"permanent_response_invalid"|"permanent_api"):
                     record(error=True) + confirm_dedup(error=True)
```

## 7. 統一エントリポイント `cost_guard.allowed()` / `finalize()`

### 7.1 シグネチャ

```python
@dataclass
class Decision:
    allowed: bool
    reason: str             # §9 reason enum
    exit_code: int          # 0 / 1 / 2
    model: str              # 実選択モデル(fallback後)
    model_class: str        # light / medium / heavy
    estimated_cost: float
    reservation_id: str | None
    dedup_key: str
    claim_id: str | None
    detail: str = ""        # error_internal 等の切り分け情報(lock_timeout / sqlite_corrupt / schema_mismatch / migration_not_run / finalize_state_mismatch 等、§9)
    script: str = ""        # finalize() が ledger.record() へ渡す呼び出し元識別子(allowed() から伝搬)
    phase: str = ""         # allowed() に渡された phase(障害解析・通知の文脈確保用、§3.2.2 finalize_state_mismatch ログにも使用)
    block_type: str = ""    # allowed() に渡された block_type(同上)

def allowed(
    phase: str,
    block_type: str,
    target_id: str = "",
    est_in: int = 200,
    est_out: int = 300,
    model_hint: str | None = None,
    script: str = "",
) -> Decision:
    """§6 実行順序の 1〜7 を実行。8(実呼び出し) は呼び出し側責務。

    成功時(allowed=True)の Decision.reason は "ok" 固定。
    失敗時の reason は §9 reason enum 14値のいずれか。

    引数 model_hint:
      - 指定された場合、models.list() で存在確認の上、優先採用
      - 存在しない場合は通常の phase→model 解決にフォールバック(警告ログ + fallback=True)
      - phase の対応クラスと食い違う場合でも、装置2閾値判定は phase のクラスを採用(§3.4)

    失敗時(allowed=False)の Decision 各フィールド既定値:
      - model = ""
      - model_class = ""
      - estimated_cost = 0.0
      - reservation_id = None
      - dedup_key = ""(compose 前で失敗した場合)
      - claim_id = None
      - detail = ""(error_internal 系のみ lock_timeout / sqlite_corrupt 等を設定)
      - script = allowed() に渡された script 値(allowed=False でも保持してログ追跡に使用)
      呼び出し側は allowed==False のとき model/model_class/reservation_id/claim_id は参照しないこと。
      detail と script は通知・障害切り分けで参照可。
    """

def finalize(
    decision: Decision,
    in_tokens: int = 0,
    out_tokens: int = 0,
    success: bool = True,
    error_kind: str = "",  # "" / "transient" / "permanent_auth" / "permanent_bad_request" / "permanent_response_invalid" / "permanent_api"
) -> None:
    """実呼び出し結果に応じて record / release / confirm_dedup / release_dedup を実行。

    error_kind → reason enum 対応表:
      ""                            → ok                       (成功時, record + confirm_dedup)
      "transient"                   → error_transient_api      (release + release_dedup, 再試行可能)
      "permanent_auth"              → error_auth               (record + confirm_dedup(error=True))
      "permanent_bad_request"       → error_bad_request        (record + confirm_dedup(error=True))
      "permanent_response_invalid"  → error_response_invalid   (record + confirm_dedup(error=True))
      "permanent_api"               → error_permanent_api      (record + confirm_dedup(error=True))

    不正引数組み合わせ:
      - success=False かつ error_kind=""        → raise ValueError("error_kind required when success=False")
      - success=True  かつ error_kind!=""       → raise ValueError("error_kind must be empty when success=True")
      raise で即座に拒否(`python -O` 最適化実行で assert が無効化されるため assert は使わない。
      運用バグの早期発見のため自動補正はしない)。

    冪等: reservation.finalized=1 または claim確定/解除済みなら no-op(2回呼ばれても安全)。
    """
```

### 7.2 呼び出し側責務
- `Decision.allowed == True` なら実LLM呼び出しを実行
- 結果に応じて `finalize(decision, ...)` を必ず呼ぶ
- `finalize` を呼ばないと予約と claim がTTLまで残る(漏れ防止のため呼び出し側でtry/finallyで保証)
- **finalize() は冪等**: reservation.finalized=1 済み もしくは claim確定/解除済みなら **no-op**(2回呼ばれても安全)

### 7.3 allowed() 段階失敗時の障害イベント記録

`allowed()` が record() 前で失敗するケース(例: claim_dedup で UNIQUE違反、reserve で DAILY_CALL_LIMIT 超過、check_phase_threshold 超過、models.list 全失敗、lock_timeout)は、`ledger.record()` を呼ばないため通常のコスト記録には残らない。

これらは以下で記録する:
- `ledger.log_event(reason: str, detail: str = "", phase: str = "", block_type: str = "")` を新規追加(§11.3 参照)
- 専用テーブル `event_log(timestamp, reason, detail, phase, block_type)` を §8.2 sqlite に追加(※下記 §8.2 テーブル設計に追記済み)
- 通知優先順位は §10 reason → 通知レベル表に従う

#### 7.3.1 allowed() 段階失敗時の log_event 呼び出しタイミング表

| 失敗段階(§6 順序) | reason | log_event 呼び出し | detail例 |
|---|---|---|---|
| 1. models.list 全失敗 | error_transient_models_list | あり | "" |
| 1. fallback 全不在 | error_model_unavailable_all_fallback | あり | "" |
| 3. 装置2 閾値超過 | stopped_phase_threshold | あり | "" |
| 4. target_id 必須違反 | error_missing_target_id | あり | block_type名 |
| 5. claim 重複 | skipped_duplicate | あり | "" |
| 6. reserve 失敗(DAILY_CALL_LIMIT 超過) | stopped_call_limit | あり | phase名 |
| 7. can_spend 失敗 | stopped_budget | あり | daily_usd / monthly_usd 値 |
| (全段階共通) BEGIN IMMEDIATE timeout | error_internal | あり | "lock_timeout" |

これらはすべて allowed() 内部で記録、`ledger.record()` 経路は通らない。`log_event` 呼び出し時は `script=allowed() に渡された script` も必ず伝搬する(§11.3)。
finalize() 内の不整合(冪等違反でない実装バグ)は `log_event(reason="error_internal", detail="finalize_state_mismatch", phase=..., block_type=..., script=...)` で記録(§3.2.2 ROLLBACK 時も同様)。

## 8. 並行制御(sqlite採用)

### 8.1 採用方針
- パス: `Path(os.getenv("STATE_DIR")) / "state.sqlite3"`(デフォルト `AppData/Local/ses_work_state`)
- §13 の `STATE_DIR` で一本化(固定パスのハードコードを廃止)
- 既存 `cost_state.json` から一回移行スクリプトで sqlite に統合
- 移行後 `cost_state.json.bak_v2.4` にリネームして readonly backup

### 8.2 テーブル設計

```sql
CREATE TABLE IF NOT EXISTS daily_state(
    date TEXT PRIMARY KEY,
    daily_usd REAL NOT NULL DEFAULT 0,
    daily_calls INTEGER NOT NULL DEFAULT 0  -- ※真実源は phase_calls の SUM(consumed)。daily_calls は読み取り簡略化用キャッシュ
);
CREATE TABLE IF NOT EXISTS monthly_state(
    month TEXT PRIMARY KEY,
    monthly_usd REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS phase_calls(
    date TEXT,
    phase TEXT,
    reserved INTEGER NOT NULL DEFAULT 0,
    consumed INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(date, phase)
);
CREATE TABLE IF NOT EXISTS reservations(
    reservation_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    phase TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finalized INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS dedup_claims(
    claim_id TEXT PRIMARY KEY,
    dedup_key TEXT NOT NULL UNIQUE,    -- UNIQUE 制約で二重 claim を防ぐ
    first_seen TEXT NOT NULL,
    ttl_sec INTEGER NOT NULL DEFAULT 3600,
    confirmed INTEGER NOT NULL DEFAULT 0,
    error INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS dedup_claims_archive(
    claim_id TEXT PRIMARY KEY,
    dedup_key TEXT NOT NULL,
    archived_at TEXT NOT NULL,
    error INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS event_log(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    reason TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    phase TEXT NOT NULL DEFAULT '',
    block_type TEXT NOT NULL DEFAULT '',
    script TEXT NOT NULL DEFAULT ''
);
```

### 8.3 排他制御
- 全更新は `BEGIN IMMEDIATE` トランザクション内で実行
- claim_dedup() は INSERT OR FAIL で UNIQUE 違反を検知
- timeout=5秒、超過は exit 2 reason=error_internal

### 8.4 真実源の宣言
- 日次コスト: `daily_state.daily_usd`(真実源)
- 月次コスト: `monthly_state.monthly_usd`(真実源)
- 日次呼び出し回数: `SUM(phase_calls.consumed) WHERE date=...`(真実源、`daily_state.daily_calls` は読み取り簡略化キャッシュ)
- phase 別予約: `phase_calls.reserved`(真実源)
- 重複起票: `dedup_claims.confirmed=1` または同 UNIQUE key(真実源)

## 9. reason enum(v2.4拡張)

| reason | exit code | 説明 | リトライ可能性 |
|---|---|---|---|
| ok | 0 | 正常 | - |
| skipped_duplicate | 2 | 装置3 重複(claim 失敗) | 不要 |
| stopped_budget | 1 | can_spend 超過 | 当日中は不可 |
| stopped_call_limit | 1 | DAILY_CALL_LIMIT 超過 | 当日中は不可 |
| stopped_phase_threshold | 1 | 装置2 閾値超過 | 入力縮小すれば可 |
| error_transient_models_list | 2 | models.list 全失敗 | 即時可(指数バックオフ) |
| error_transient_api | 2 | API 429/5xx | 即時可(指数バックオフ) |
| error_model_unavailable_all_fallback | 2 | 同クラス代替も不在 | 環境改善後 |
| error_permanent_api | 2 | 一般的な4xx | 不可(要調査) |
| error_auth | 2 | 401/403 | 不可(要トークン更新) |
| error_bad_request | 2 | 400(入力不正) | 入力修正後 |
| error_response_invalid | 2 | レスポンスJSON不正/parse失敗 | 不可(要調査) |
| error_missing_target_id | 2 | block_type が target_id 必須なのに未指定(設定不備/呼び出し側契約違反) | 入力修正後 |
| error_internal | 2 | sqlite破損 / schema不整合 / 移行未実施 / ロック取得失敗 / finalize トランザクション中途破綻 等(target_id未指定は error_missing_target_id へ分離)。detail 推奨値: `lock_timeout` / `sqlite_corrupt` / `schema_mismatch` / `migration_not_run` / `finalize_state_mismatch` | 不可(要調査・detail フィールドで原因記録) |

## 10. 通知優先順位(reason → 通知レベル)

| 優先度 | reason | LINE残通数による降格 |
|---|---|---|
| 1 | EMERGENCY_USD 超過 | 残通数チェックなし |
| 2 | error_model_unavailable_all_fallback / error_internal / error_auth / DAILY_HARD_USD 超過 | 残通数<10で log only |
| 3 | stopped_budget / MONTHLY_USD 超過 / error_permanent_api / error_response_invalid | 残通数<30で log only |
| 4 | stopped_phase_threshold / error_bad_request / error_missing_target_id | 残通数<30で log only |
| 5 | stopped_call_limit / error_transient_*(連続3回未満) | 通常 log only |
| なし | ok / skipped_duplicate | 通知しない |

連続3回ルール: 同一 phase で `error_transient_*` が 連続3回発生 → その時点で優先度3に昇格して push

## 11. ledger.py 拡張(既存シグネチャ温存)

### 11.1 既存(変更なし、後方互換保証)
```python
def can_spend(est_in: int = 200, est_out: int = 300, model: str = "") -> bool: ...
def daily_total() -> float: ...
def monthly_total() -> float: ...
```

### 11.2 record() の kwargs 拡張(既存呼び出しは無修正で動く)
```python
def record(
    in_tokens: int, out_tokens: int, model: str, script: str,
    *,
    phase: str | None = None,
    reservation_id: str | None = None,
    fallback: bool = False,
    unknown_model: bool = False,
    error: bool = False,
    reason: str | None = None,
    detail: str | None = None,
) -> None: ...
```

### 11.3 新規追加
```python
def reserve(phase: str) -> str | None: ...
def release(reservation_id: str) -> None: ...
def claim_dedup(dedup_key: str, ttl_sec: int = 3600) -> str | None: ...
def release_dedup(claim_id: str) -> None: ...
def confirm_dedup(claim_id: str, error: bool = False) -> None: ...
def check_daily_limit(phase: str) -> bool:
    """監視・モニタリング用のみ。本番判定では reserve() を使うこと。"""
def log_event(reason: str, detail: str = "", phase: str = "", block_type: str = "", script: str = "") -> None:
    """allowed() 段階の失敗(record前で終わるケース)を event_log テーブルに記録する。
    例: skipped_duplicate / stopped_call_limit / stopped_phase_threshold / error_transient_models_list / error_internal(lock_timeout) / finalize_state_mismatch など。
    `script` は allowed() に渡された呼び出し元識別子(allowed段階失敗でも追跡粒度を finalize 経路と揃えるため伝搬)。
    通知は §10 reason → 優先度マップに従って notifier 側で実行。
    """
    ...

def estimate_cause(state: dict) -> str:
    """停止理由を人間可読な文字列で返す。
    例:
      input  state={'monthly_usd': 145.32, 'monthly_limit': 140.0}
      output 'monthly_usd $145.32 > $140.0 (MONTHLY_USD)'

      input  state={'reason': 'error_internal', 'detail': 'lock_timeout'}
      output 'internal error: lock_timeout (sqlite BEGIN IMMEDIATE timeout=5s)'
    """
```

## 12. models.list() 失敗時の運用要件(v2.4で統一)

- 即時リトライ: 2回(指数バックオフ 1秒, 3秒)
- 同一プロセス内の `models.list()` 結果は5分キャッシュ
- 全リトライ失敗 → **select_model を中断、即 exit 2 reason=error_transient_models_list**
- `available_models=set()` で fallback 試行する旧仕様は廃止(v2.3 までの仕様)
- 連続3回失敗(別プロセス含む)で優先度3に昇格して LINE push

## 13. 定数集約(.env)

```ini
# 装置1
DAILY_CALL_LIMIT_DEFAULT=30
DAILY_CALL_LIMIT_IMPLEMENTATION=10
PHASE_MODEL_RESEARCH=gpt-4o-mini
PHASE_MODEL_REQUIREMENTS=gpt-4o-mini
PHASE_MODEL_TEST=gpt-4o-mini
PHASE_MODEL_DESIGN=gpt-5.4
PHASE_MODEL_PRE_IMPL=gpt-5.4
PHASE_MODEL_IMPLEMENTATION=codex-5

# 装置2
PHASE_THRESHOLD_LIGHT=0.025
PHASE_THRESHOLD_MEDIUM=0.10
PHASE_THRESHOLD_HEAVY=0.15

# 装置3
DEDUP_CLAIM_TTL_SEC=3600

# ledger / cost_guard
COST_GUARD_DAILY_USD=8.0
COST_GUARD_DAILY_SOFT_USD=6.0
COST_GUARD_MONTHLY_USD=140.0
COST_GUARD_EMERGENCY_USD=300.0

# 並行制御 / ストレージ
STATE_DIR=%LOCALAPPDATA%\ses_work_state
SQLITE_TIMEOUT_SEC=5
```

## 14. テスト計画

- test_phase_threshold.py
- test_dedup_claim.py(claim方式 INSERT 検証)
- test_call_limit.py
- test_judge_order.py(§6 順序)
- test_exit_code2.py
- test_call_limit_race.py(2プロセス並行)
- test_dedup_claim_race.py(2プロセス並行で UNIQUE違反検知)
- test_models_list_failure_reason.py(リトライ後 error_transient_models_list)
- test_duplicate_does_not_consume_daily_call.py
- test_reservation_rollback.py(transient失敗で release)
- test_dedup_claim_transient_release.py(transient失敗で release_dedup → 再claim可能)
- test_v2_v3_no_mixed_call.py(matching_v2 直接呼び出しが残っていない)
- test_missing_target_id_reason.py(必須block_typeでtarget_id未指定 → reason=error_missing_target_id)
- test_dedup_claim_ttl_inline_purge.py(claim_dedup内で期限切れ未確定claimをトランザクション内purge)
- test_dedup_claim_expired_reclaim.py(claim → finalizeなし → TTL経過 → 再claim成功)
- test_finalize_idempotent.py(finalize 2回呼び出しでも safe)
- test_finalize_permanent_kinds.py(permanent_auth / permanent_bad_request / permanent_response_invalid / permanent_api)
- test_reserved_decrement.py(成功/permanent失敗時に phase_calls.reserved が確実に -1 されることを検証)
- test_lock_timeout_internal.py(BEGIN IMMEDIATE timeout=5s 到達時に reason=error_internal, detail="lock_timeout" を返す)
- test_finalize_invalid_args.py(success=False かつ error_kind=""、success=True かつ error_kind!="" の不正組み合わせで `raise ValueError`)
- test_model_hint.py(model_hint 指定時の優先採用 / 不在時の通常解決フォールバック)
- test_decision_detail.py(error_internal 時に Decision.detail に lock_timeout / sqlite_corrupt 等が設定される)
- test_decision_script.py(allowed() に渡した script が Decision.script に保持され、finalize() が ledger.record(... script=...) で正しく渡す)
- test_finalize_atomicity.py(finalize 内で record/release/confirm_dedup/release_dedup の途中失敗を仕込み、全操作が ROLLBACK されることを検証)

## 15. ロールバック手順

- `cost_guard_v2/` 以下を削除
- `common/ledger.py` を git で revert
- `cost_guard.py` を git で revert
- sqlite を削除し `cost_state.json.bak_v2.4` を `cost_state.json` に rename
- `.env` から v2.4 で追加した変数を削除

## 16. 変更履歴

| 日付 | バージョン | 内容 |
|---|---|---|
| 2026-06-16 | v2.0 | 初版 |
| 2026-06-16 | v2.1 | gpt-5.4レビュー反映(7項目) |
| 2026-06-16 | v2.2 | 判定順序統一/装置3完全スキップ/models.list set() |
| 2026-06-16 | v2.3 | gpt-5.4ゲート①反映(統一エントリ/sqlite/reason enum/予約方式) |
| 2026-06-16 | v2.4 | gpt-5.4ゲート①再反映(claim方式/reason enum拡張/models.list統一/target_id必須マップ/STATE_DIR一本化/真実源宣言/check_daily_limit用途制限) |
| 2026-06-16 | v2.5 | gpt-5.4ゲート①三反映(error_missing_target_id 新設 14値化 / TTL inline purge による実効値化 / Decision.reason "ok" 固定 / finalize 冪等性 / error_internal detail フィールド) |
| 2026-06-16 | v2.6 | gpt-5.4ゲート①四反映: §5.3 本文を inline purge 仕様に完全書き換え / purge条件SQL明文化 / archive条件明文化(confirmed=1のみ) / §7.1 docstring 成功時 reason=ok 明記 / ledger.record に reason/detail 引数追加 |
| 2026-06-16 | v2.7 | gpt-5.4ゲート①五反映: §14 矛盾テスト(test_dedup_ttl_expiry.py)削除 / §5.3 言い回し補正("履歴が残る"→"再claim後の新レコードのみ残る") / §7.1 allowed/finalize docstring に reason=ok 固定と error_kind→reason 対応表を本文化 / §9 error_internal の detail 推奨値例(lock_timeout等4種)列挙 |
| 2026-06-16 | v2.8 | gpt-5.4ゲート①六反映: §3.2.1 に reserved 減算明記(成功/transient/permanent 全パターン)/ §7.1 allowed/finalize docstring に失敗時 Decision既定値・model_hint仕様・finalize不正引数仕様を本文化 / §7.3 新設(allowed段階失敗の event_log 記録)/ §8.2 event_log テーブル追加 / §11.3 ledger.log_event() 新規 / §14 テスト4本追加 |
| 2026-06-16 | v2.9 | gpt-5.4ゲート①七反映: §7.1 Decision に detail/script フィールド追加 / allowed() シグネチャに script: str 追加 / 失敗時 Decision 既定値に detail/script 明記 / finalize() の assert を raise ValueError に変更(-O 対策) / §7.3.1 log_event 呼び出しタイミング表追加(8段階) / §14 テスト2本追加(test_decision_detail / test_decision_script) |
| 2026-06-16 | v2.10 | gpt-5.4ゲート①八反映: §3.2.2 新設(finalize 原子性: 6操作を単一 BEGIN IMMEDIATE 内で実行、public/_in_tx 分離方針)/ §7.1 Decision に phase/block_type 追加 / §8.2 event_log に script 列追加 / §11.3 log_event に script 引数追加 / §9 error_internal.detail に finalize_state_mismatch 追加 / §14 test_finalize_invalid_args の例外を ValueError に修正 + test_finalize_atomicity.py 追加 |
