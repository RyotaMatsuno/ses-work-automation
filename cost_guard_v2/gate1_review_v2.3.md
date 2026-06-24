# ゲート① レビュー結果(SPEC v2.3)

レビュー日時: 2026-06-16T18:26:37.921112
モデル: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 6426, "completion_tokens": 2137, "total_tokens": 8563, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 303, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

## 前回指摘の解消状況

1. **実行順序の明記** — ✅  
   §6で `dedup → select_model → estimate → phase_threshold → reserve(check_daily_limit内包) → can_spend → 実呼び出し → finalize` に固定され、前回の順序不整合は概ね解消されています。

2. **DAILY_CALL_LIMIT のカウント更新タイミング** — ✅  
   §3.2.1 で事前予約方式、成功時確定、transient失敗時release、permanent失敗時確定まで明文化されており、実装差が出にくくなっています。

3. **ledger / dedup_state の排他制御** — ⚠  
   sqlite + `BEGIN IMMEDIATE` 採用は前進です。  
   ただし**重複起票防止そのものはまだ完全には解消していません**。現仕様は  
   `is_duplicate()` で確認 → 実呼び出し → 成功/恒久失敗時に `mark(dedup_key)`  
   なので、**2プロセスが同じ dedup_key をほぼ同時に `is_duplicate=False` で通過し、二重実行する競合**が残ります。排他基盤は入ったが、dedupの業務要件は未達です。

4. **exit code 2 の機械判定可能化** — ✅  
   §9 reason enum で `skipped_duplicate / error_transient_models_list / error_transient_api / error_model_unavailable_all_fallback / error_internal` が分かれ、前回懸念は解消方向です。

5. **`is_allowed()` の責務範囲と装置2の位置** — ✅  
   `cost_guard.allowed()` を統一エントリポイントとして定義し、§7で1〜7を担当、装置2もその中に入ることが明記されています。

6. **dedup_key 粒度の粗さ** — ⚠  
   `target_id` 追加は改善です。  
   ただし `target_id` 省略時に空文字フォールバックを許容しており、**旧呼び出し側が未改修のままだと依然として粗粒度 dedup が発生**します。前回指摘の本質は「正当な別件起票を潰さないこと」なので、完全解消とは言い切れません。

7. **`models.list()` 失敗時の運用要件** — ⚠  
   即時リトライ回数、バックオフ、通知昇格条件まで入った点は良いです。  
   ただし §12 の  
   「全失敗 → `available_models=set()` で fallback経路 → 不在なら `error_transient_models_list`」  
   は仕様表現が曖昧です。`available_models=set()` なら通常は必ず“不在”になるため、**fallback経路に進める意味が薄く、実装者に誤読余地**があります。

8. **通知優先順位と停止理由の対応表** — ✅  
   §9 と §10 で reason / exit code / 通知レベルの対応が整理され、運用判断しやすくなっています。

---

## 新たな必須修正項目

- **dedup を「事後 mark」ではなく「事前 claim」に変更してください。**  
  現行 §6 の  
  `is_duplicate(dedup_key)` → 実呼び出し → `mark(dedup_key)`  
  では、並行実行時に同一 dedup_key の二重実行を防げません。  
  必須対応案:
  - `claim_dedup(dedup_key)` をトランザクション内で実行し、**最初の1件だけ INSERT 成功**
  - 後続は `UNIQUE constraint` で `skipped_duplicate`
  - 実呼び出し前に claim し、成功時/恒久失敗時は確定、transient失敗時の扱いを明記  
    - 例1: transient時は claim解除して再試行可能にする  
    - 例2: transient時も一定TTL付きで保持する  
  この点は**装置3の目的そのもの**なので必須です。

- **`finalize(..., error_kind="permanent")` の reason enum を具体化してください。**  
  §7.2 では permanent 失敗時に `record + mark with error=True` とありますが、§9 の reason enum には  
  - 一般的な 4xx
  - 認証/権限
  - 入力不正
  - レスポンス形式不正  
  などの**恒久失敗の受け皿 reason**が不足しています。  
  今のままだと `error_*` が抽象的すぎて、呼び出し側・通知側で扱いがぶれます。  
  最低でも `error_permanent_api` か、可能なら `error_auth / error_bad_request / error_response_invalid` などに整理してください。

- **`models.list()` 全失敗時の分岐仕様を一本化してください。**  
  §3.3 と §12 の書き方だと、  
  - `models.list()` 失敗時は fallback を試みるのか
  - それとも即 `error_transient_models_list` にするのか  
  が読み手によって揺れます。  
  `available_models=set()` を使うなら実質 fallback 判定不能なので、  
  **「全失敗時は select_model を中断し、reason=error_transient_models_list で即終了」**  
  のように単純化した方が安全です。

- **`target_id` 未指定を許容する条件を制限してください。**  
  現状の「空文字で後方互換」は移行期には便利ですが、運用に入ると**別件の正当な起票抑止事故**を残します。  
  少なくとも
  - `block_type` ごとに `target_id` 必須/任意を定義
  - 必須系で未指定なら `exit 2 reason=error_internal` ではなく、明示的に設定不備扱い
  を仕様化してください。

---

## 推奨項目

- **state.sqlite3 のパスは `STATE_DIR` 前提の実パス解決ルールを明記するとよいです。**  
  §8.1 に固定パス、§13 に `STATE_DIR` があり、少し二重定義気味です。Windows依存緩和のためにも  
  `Path(os.getenv("STATE_DIR")) / "state.sqlite3"`  
  のように一本化を推奨します。

- **`phase_calls.reserved / consumed` と `daily_state.daily_calls` の関係を注記すると保守しやすいです。**  
  何を真実源とするかが曖昧だと、障害時復旧や整合性確認で迷います。

- **`error_internal` にロック取得失敗以外の何を含めるか例示を追加するとよいです。**  
  例: sqlite破損、移行未実施、schema不整合など。運用切り分けが速くなります。

- **`check_daily_limit()` を“監視用で本番判定には使わない”とさらに強く書くことを推奨します。**  
  せっかく `reserve()` に一本化しているので、誤用予防のためです。

- **テスト計画に `test_dedup_claim_transient_release.py` 相当を追加推奨です。**  
  dedupを事前claim方式に直すなら、transient失敗後に再実行可能かの確認が重要です。
