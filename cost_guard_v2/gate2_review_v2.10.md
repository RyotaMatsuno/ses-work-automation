# ゲート② レビュー(cost_guard_v2 実装、SPEC v2.10 準拠)

日時: 2026-06-17T13:32:08.544640
model: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 23412, "completion_tokens": 4037, "total_tokens": 27449, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 2198, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}
対象ファイル: ['cost_guard_v2/SPEC.md', 'cost_guard.py', 'common/ledger.py', 'common/state_store.py', 'common/dedup.py']

---

NG

- **`common/ledger.py::_record_in_tx()` の冪等性判定が危険です。**  
  `reservation_id` が存在しない場合まで `return` しており、**成功/恒久失敗 finalize で `record` がスキップされたまま `confirm_dedup` だけ commit され得ます**。  
  これは **SPEC §3.2.2 / §7.2 不整合** かつ **サイレントなデータ欠損**です。  
  - 現状: `res_row is None or finalized == 1 -> no-op`
  - 必要:  
    - `finalized == 1` は冪等 no-op 候補  
    - **`res_row is None` は state mismatch として例外化**し、outer finalize で ROLLBACK + `finalize_state_mismatch` 記録

- **`_confirm_dedup_in_tx()` / `_release_dedup_in_tx()` が claim 不在を無条件 no-op 扱いしており、冪等性の範囲を超えています。**  
  SPEC §7.2 の no-op は「**既に finalize 済みの再呼び出し**」のためのものです。  
  しかし現実装だと、**初回 finalize でも claim 行消失を黙殺**でき、  
  - success/permanent: 予約消費・コスト計上だけされて dedup 未確定  
  - またはその逆  
  のような **整合性破綻を commit** し得ます。  
  **outer `finalize()` で reservation / claim の事前整合チェックを行い、片側欠損は `finalize_state_mismatch` で失敗させる**べきです。

- **Cursor追加の `_record_in_tx()` 冪等性チェックは、現状のままでは SPEC §7.2 と整合していません。**  
  SPEC の意図は「二重 finalize を安全化」であり、**不正状態の隠蔽**ではありません。  
  今の実装は `reservation.finalized=1` だけで no-op に寄せており、claim 側状態との突合せがありません。  
  **冪等 no-op の成立条件を outer `finalize()` 側で明示的に定義**すべきです。  
  例:
  - `reservation.finalized=1` かつ claim が confirm/release 済み → no-op
  - それ以外の欠損/片肺状態 → 例外

- **`common/ledger.py::log_event()` が `BEGIN IMMEDIATE` を使っておらず、SPEC §8.3「全更新は BEGIN IMMEDIATE」から外れています。**  
  単発 INSERT の autocommit でも動くことはありますが、**lock timeout 振る舞いが他更新系と不統一**になり、SPEC §7.3 / §9 の `error_internal(lock_timeout)` 運用とズレます。  
  少なくとも public 更新 API は **明示トランザクション化**すべきです。

- **`allowed()` の stopped_budget 時の `log_event.detail` が SPEC §7.3.1 の期待粒度に達していません。**  
  SPEC は `daily_usd / monthly_usd` 値の記録を想定していますが、実装は空文字です。  
  これは致命傷ではないですが、**障害解析性が仕様未達**です。

### 推奨項目
- `finalize()` に **事前状態検証ヘルパ**を追加  
  例: `_load_finalize_state_in_tx(conn, reservation_id, claim_id)` で reservation/claim の存在・finalized/confirmed を一括確認。
- `Reasons` は戻り値で一貫して `str` 化するか、型注釈を `Reasons | str` に寄せると保守しやすいです。
- `allowed()` の `_notify()` にも `script` を渡せる設計だと追跡性が上がります。
- `claim_dedup()` の purge SQL はコメントで「row.ttl_sec を使う設計」か「関数引数 ttl_sec を使う設計」か明記すると誤読防止になります。

---

## 質問への回答

### 1. SPEC v2.10 と実装に致命的な乖離はあるか
**あります。**  
最大の乖離は **finalize 冪等性実装が state mismatch を no-op で飲み込む点**です。  
これは **SPEC §3.2.2 / §7.2 の意図逸脱**で、しかも **静かにデータ整合性を壊し得る**ため致命的です。

### 2. finalize の原子性(§3.2.2)は正しく実装されているか
**半分 Yes、半分 No です。**
- Yes: `cost_guard.finalize()` が **単一 `BEGIN IMMEDIATE`** で `_record_in_tx / _release_in_tx / _confirm_dedup_in_tx / _release_dedup_in_tx` を呼んでおり、**トランザクション構造自体は仕様通り**です。
- No: ただし内部 `_in_tx` が **不整合を例外化せず no-op** にしているため、**原子的に“壊れた結果”を commit できてしまう**。  
  したがって、**原子性の箱はあるが、中身の整合性保証が不足**しています。

### 3. claim TTL inline purge(§5.3)は正しく実装されているか
**概ね Yes です。**
- `claim_dedup()` 内で
  - `BEGIN IMMEDIATE`
  - `confirmed=0` の期限切れ claim を DELETE
  - 新規 INSERT
  を **同一トランザクションで実行**しており、SPEC §5.3 の主旨に合っています。

補足:
- SQL は既存行の `ttl_sec` 列を使う実装です。これは実運用上は自然ですが、仕様解釈を明文化するとより安全です。

### 4. 冪等性チェック(Cursor 追加分)に問題はないか
**問題あります。**
- `reservation.finalized=1` を no-op 条件にする発想自体は方向性として妥当です。
- ただし現実装は **「再実行安全化」ではなく「不整合隠蔽」**になっています。  
  特に `res_row is None` まで no-op にしているのは危険です。

### 5. 本番デプロイ(sqlite 移行済み)を継続して良いか、それともロールバックすべきか
**現状のまま継続は非推奨、実質ロールバック推奨です。**
- 理由: **silent data corruption / silent undercount** のリスクがあるため。
- 最低条件:
  1. finalize の事前整合チェック追加
  2. `_record_in_tx` の `res_row is None -> no-op` 廃止
  3. claim 側 missing row の扱いを outer finalize で厳密化
  4. 追加で `test_finalize_atomicity` に **reservation missing / claim missing / 片側のみ完了** ケースを増やす

**結論:**  
SQLite 移行データ自体を即破棄する必要までは断定しませんが、**この finalize 実装のまま本番運用継続は NG**です。  
少なくとも **新規トラフィックは止めて修正後に再開**を推奨します。
