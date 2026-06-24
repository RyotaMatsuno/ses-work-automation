# ゲート① レビュー(SPEC v2.8)

日時: 2026-06-16T22:02:04.834215
model: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 8944, "completion_tokens": 2074, "total_tokens": 11018, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 512, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

まず、**v2.7で指摘した必須1＋推奨5の反映状況**を確認します。

- **必須: §3.2.1 reserved 減算明記**  
  → **解消済み**。成功 / transient失敗 / permanent失敗の全パスで `phase_calls.reserved -= 1` が明文化されています。
- **推奨: Decision既定値**  
  → **解消済み**。§7.1 に失敗時既定値が明記されています。
- **推奨: finalize不正引数**  
  → **解消済み**。§7.1 に不正組み合わせ時の挙動が追記されています。
- **推奨: allowed段階失敗の event_log**  
  → **概ね解消済み**。§7.3 / §8.2 / §11.3 が追加されています。
- **推奨: lock_timeout テスト**  
  → **テスト追加は解消済み**。ただし後述の通り、**仕様本体は 아직不整合が残っています**。
- **推奨: model_hint 仕様**  
  → **解消済み**。優先採用・不在時フォールバックが明記されています。

## 修正必須項目

- **Decision に `detail` が無く、`error_internal.detail` 運用と `test_lock_timeout_internal.py` の期待値と整合していません。**  
  §9 では `error_internal` の `detail` を重要運用情報として扱い、§11.3 `estimate_cause()` も `detail` 前提、§14 では **`reason=error_internal, detail="lock_timeout" を返す`** テストまで定義しています。  
  しかし §7.1 の `Decision` dataclass には `detail` フィールドが存在しません。このままだと:
  - `allowed()` の戻り値だけでは `lock_timeout` / `sqlite_corrupt` / `schema_mismatch` / `migration_not_run` を呼び出し側が受け取れない
  - §14 のテスト期待を満たせない
  - exit code / reason / detail を使った通知や切り分けが仕様通り実装できない  
  **対応案:** `Decision.detail: str = ""` を追加し、`allowed()` 失敗時および `finalize()` 内部エラー時に設定すること。

- **`finalize()` から `ledger.record()` を呼ぶための `script` 情報の受け渡しが仕様化されておらず、既存 `ledger.record()` シグネチャと接続できません。**  
  §11.2 では `ledger.record(in_tokens, out_tokens, model, script, *, ...)` の **`script` が必須位置引数** のままです。一方、§7.1 の `Decision` と `finalize()` の引数には `script` が存在しません。  
  そのため仕様どおりだと `finalize()` は `record()` を正しく呼べません。これは「既存シグネチャ温存」と「統一エントリポイント finalize()」の間の致命的不整合です。  
  **対応案はどちらかに統一が必要です。**
  1. `allowed(..., script: str)` / `Decision.script` を追加し、`finalize()` がそれを使って `record()` する  
  2. もしくは `ledger.record()` の `script` を optional 化するが、これは「既存変更なし」の文言を修正する必要あり  
  現状のままでは実装仕様として閉じていません。

## 推奨項目

- **`finalize()` の不正引数検査で「assert」を使う表現は避け、常時有効な明示例外にした方が安全です。**  
  Python の `assert` は最適化実行で無効化され得ます。仕様としては `raise AssertionError(...)` か `raise ValueError(...)` を明示した方が運用事故を防げます。

- **§7.1 の「失敗時 Decision 各フィールド既定値」と、実際の失敗段階ごとの値保持方針を分けて書くとよいです。**  
  たとえば `claim_dedup` 後に `reserve` 失敗した場合、`dedup_key` や `claim_id` は一瞬存在し、その後 release されます。「常に空/None」と読むと誤解を招きます。  
  `compose前失敗時の最低保証値` と `途中失敗時の返却値方針` を分けると実装者が迷いません。

- **`allowed()` 失敗時の `log_event()` 記録タイミングを、各失敗分岐ごとに明示すると実装漏れを減らせます。**  
  特に `skipped_duplicate`、`stopped_call_limit`、`stopped_budget`、`stopped_phase_threshold`、`error_transient_models_list`、`error_internal` は明示されていますが、`error_missing_target_id` や `error_model_unavailable_all_fallback` も対象に含むかを列挙すると確実です。

- **`daily_state.daily_calls` キャッシュの更新責務を明記した方がよいです。**  
  §8.4 で真実源は `SUM(phase_calls.consumed)` とされていますが、キャッシュ `daily_state.daily_calls` をいつ誰が更新するか不明です。`record()` 時に同期更新するのか、再計算するのかを固定すると不整合を防げます。

- **既存呼び出し側との互換性確認項目に、各呼び出し元が `try/finally` で `finalize()` を保証するテスト観点を追加するとよいです。**  
  今回の設計では未finalizeが reservation/claim リークの主因になるため、互換性は「呼べる」だけでなく「漏れなく finalize する」に依存します。`matching_v3 / mail_pipeline / gate_checker / freee / line_webhook` ごとの導入確認があると安心です。

総評として、**v2.7での指摘事項はほぼ反映できています**。ただし今回の v2.8 では、**`Decision.detail` 欠落** と **`finalize()`→`ledger.record()` の `script` 受け渡し欠落** が、実装成立性の観点でまだ必須修正です。ここを直せば GO に近いです。
