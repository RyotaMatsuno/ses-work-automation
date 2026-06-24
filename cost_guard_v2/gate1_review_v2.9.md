# ゲート① レビュー(SPEC v2.9)

日時: 2026-06-16T22:05:40.955598
model: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 9848, "completion_tokens": 2053, "total_tokens": 11901, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 588, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

まず前回指摘の反映確認です。

- **必須1: `Decision.detail` 追加** → **解消済み**
  - §7.1 `Decision.detail: str = ""` 追加あり
  - allowed() 失敗時既定値にも `detail` 記載あり
  - §14 `test_decision_detail.py` 追加あり
- **必須2: `script` 伝搬** → **解消済み**
  - §7.1 `Decision.script` 追加あり
  - `allowed(..., script="")` 追加あり
  - 失敗時既定値でも `script` 保持を明記
  - §14 `test_decision_script.py` 追加あり
- **推奨: assert→raise** → **解消済み**
  - §7.1 finalize() の不正引数チェックが `raise ValueError` に変更済み
- **推奨: log_event 呼び出しタイミング列挙** → **解消済み**
  - §7.3.1 タイミング表追加済み

## 修正必須項目

- **§14 の `test_finalize_invalid_args.py` が仕様本文と矛盾している**
  - 現在のテスト計画では  
    `test_finalize_invalid_args.py(... の不正組み合わせで AssertionError)`  
    となっていますが、§7.1 では明確に **`raise ValueError`** と定義済みです。
  - v2.9 で assert→raise に変えた主目的そのものと衝突しており、このままだと実装かテストのどちらかが必ず不一致になります。
  - **修正内容**: §14 の期待例外を **AssertionError → ValueError** に修正すること。

- **finalize における「record/release と dedup confirm/release の原子性」が未規定で、装置1〜3整合性に穴がある**
  - §3.2.1 では finalize 時の reservation / phase_calls 更新は「**全て BEGIN IMMEDIATE トランザクション内、原子的**」と書かれています。
  - しかし §6・§7.1 の記述では、success/permanent/transient 時に行う  
    `record / release / confirm_dedup / release_dedup`  
    が**同一トランザクションで一括実行されるのか**、それとも関数ごと個別トランザクションなのかが不明です。
  - ここが曖昧なままだと、たとえば
    - success: `record` と `reserved -= 1` は完了したが `confirm_dedup` 前にプロセス断
    - transient: `release(reservation_id)` は完了したが `release_dedup(claim_id)` 前に断
    といった**中途半端な状態**が発生し得ます。
  - これは今回のレビュー観点である **装置1〜3 + event_log + reserved減算 の整合性** に対する致命的な未確定点です。
  - **修正内容**:
    - finalize(success/transient/permanent) で行う
      - reservations.finalized 更新
      - phase_calls.reserved/consumed 更新
      - ledger.record または release
      - confirm_dedup または release_dedup
    を**単一 sqlite トランザクションで原子的に実行する**ことを本文に明記してください。
    - 併せて `ledger.record() / release() / confirm_dedup() / release_dedup()` が単体で勝手に別トランザクションを開始しないのか、または「内部関数化して finalize が外側トランザクションを持つ」のか、実装方式も規定が必要です。

## 推奨項目

- **`Decision` に `phase` / `block_type` を保持した方がよい**
  - 現状でも reservation テーブルや dedup_key から復元可能な設計にはできますが、`finalize()` 内部で `log_event(reason="error_internal", detail="finalize_state_mismatch")` を出す際の文脈が不足しがちです。
  - 障害解析・通知品質のため、`Decision` に `phase` / `block_type` を持たせると保守しやすくなります。

- **`allowed=False` 時の Decision 既定値の説明を「早期失敗時の最低保証値」と明確化した方がよい**
  - 現文面だと、たとえば step6 reserve 失敗のように model や estimated_cost が既に確定していても、必ず空/0.0を返すのか、最低保証としてそう扱うだけなのかが読みにくいです。
  - 実装の自由度と利用者期待を揃えるため、意味づけを明文化するとよいです。

- **event_log の `script` 欄がないため、allowed段階失敗の追跡粒度が finalize 経路より粗い**
  - v2.9 で script 伝搬を直した意図からすると、`allowed()` 内で落ちたケースも event_log に script を残せると運用上かなり有効です。
  - 必須ではないですが、障害調査性は上がります。

- **`error_internal.detail` の列挙に finalize 系の代表値を §9 に追記するとよい**
  - §7.3 では `finalize_state_mismatch` が出てきますが、§9 の推奨 detail 例には未掲載です。
  - `lock_timeout / sqlite_corrupt / schema_mismatch / migration_not_run / finalize_state_mismatch` のように揃えると運用が安定します。

総評として、**前回の必須2件と推奨2件は概ね解消**されています。  
ただし、**`ValueError` と `AssertionError` の仕様不一致**、および **finalize 全体の原子性未規定** は、実装・試験・運用のいずれにも直結するため、ここは修正してから進めるべきです。
