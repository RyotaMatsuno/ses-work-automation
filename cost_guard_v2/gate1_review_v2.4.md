# ゲート① レビュー結果(SPEC v2.4)

レビュー日時: 2026-06-16T18:31:56.600180
モデル: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 7564, "completion_tokens": 1929, "total_tokens": 9493, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 358, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

## 前回(v2.3)必須指摘の解消状況

1. **dedup を「事後 mark」ではなく「事前 claim」に変更** — ✅  
   §5.2, §6, §8.2, §11.3 で `claim_dedup()` + sqlite `UNIQUE(dedup_key)` による事前claimへ変更されており、前回の並行二重実行リスクは仕様上きちんと潰せています。  
   `skipped_duplicate` への分岐、transient時の `release_dedup()` も明記されており、装置3の中核要件は解消済みです。

2. **permanent失敗の reason enum 具体化** — ✅  
   §6, §7.1, §9 で  
   `error_permanent_api / error_auth / error_bad_request / error_response_invalid`  
   に分解され、前回の「恒久失敗の受け皿が抽象的すぎる」問題は解消されています。

3. **`models.list()` 全失敗時の分岐仕様一本化** — ✅  
   §3.3 と §12 が  
   **「全失敗 → select_model を中断し、即 `error_transient_models_list`」**  
   に統一され、v2.3 にあった `available_models=set()` 経由の誤読余地は解消されています。

4. **`target_id` 未指定許容条件の制限** — ⚠  
   §5.4 で block_type ごとの required/optional 宣言が入り、粗粒度dedupの放置状態からは大きく改善しています。  
   ただし、**必須系で未指定時の扱いが依然 `error_internal` のまま**で、前回指摘の  
   「`error_internal` ではなく、明示的な設定不備/入力不備として扱う」  
   までは到達していません。  
   制約導入自体は良いですが、reason設計としては未完です。

---

## 新たな必須修正項目

- **`target_id` 必須違反を `error_internal` から分離してください。**  
  現仕様では §5.4, §6, §9, §14 すべてで、必須block_typeなのに `target_id` 未指定のケースが `error_internal` 扱いです。  
  これは以下の点で不適切です。
  - 呼び出し側の入力不備/契約違反なのに、sqlite破損やschema不整合と同列になる
  - 通知優先度が過大になりやすい
  - 運用上の切り分けが悪い

  最低限、以下のいずれかに分離することを必須とします。
  - `error_missing_target_id`
  - `error_invalid_argument`
  - `error_config_block_type_contract`

  併せて §9 の reason enum、§10 の通知優先度、§14 のテスト名も更新してください。

- **dedup claim TTL の失効仕様を、`週次cronでarchive` ではなく“実効TTL”になるように修正してください。**  
  §5.3 では「TTL超過で再試行可能」と読めますが、実際の記述は  
  **「確定/解除されないまま TTL 超過 → 週次cronで archive へ移動」**  
  です。  
  このままだと、TTL=3600秒でも、最悪では**次の週次cronまで UNIQUE制約で再claim不能**になり、TTLが実効値になっていません。

  仕様としては次のどちらかに一本化が必要です。
  - **案A:** `claim_dedup()` 実行時に `first_seen + ttl_sec` を見て、期限切れclaimを同トランザクション内で回収してからINSERTする
  - **案B:** 少なくとも分単位/時単位の定期ジョブでexpire処理し、週次archiveは別用途にする

  現状のままだと、異常終了後の再実行性が仕様上保証されません。これは運用事故に直結するため必須です。

---

## 推奨項目

- **`Decision.reason` の初期値/成功時値を明記すると実装ぶれが減ります。**  
  例えば `allowed()` 成功時は必ず `reason="ok"` を返す、と固定しておくと呼び出し側の分岐が単純になります。

- **`model_hint` の優先順位と制約を明文化するとよいです。**  
  §7.1 に引数はありますが、  
  - `model_hint` が phase推奨モデルより優先されるのか
  - 同クラス外hintを許可するのか
  - hint不在時のfallback対象はどこまでか  
  が本文では読み取りにくいです。

- **`finalize()` の冪等性方針を明記すると安全です。**  
  呼び出し側に `try/finally` を要求しているため、二重呼び出し防止・再実行時の扱いを仕様化しておくと事故防止になります。  
  例:
  - `reservation.finalized=1` 済みなら no-op
  - `claim_id` 確定済み/解除済みなら no-op

- **`daily_state.daily_calls` キャッシュの更新責務を明記するとよいです。**  
  真実源が `SUM(phase_calls.consumed)` なのは明快ですが、キャッシュ更新タイミング  
  （record時のみ更新 / リカバリ時再集計 / 不整合検知時再構築）  
  を書いておくと保守しやすいです。

- **`timeout=5秒` のエラー詳細を reason補助情報で標準化すると運用が楽です。**  
  reason自体は `error_internal` でよいとしても、`detail=lock_timeout` のような補助フィールドを ledger/log に必須記録すると切り分けが速くなります。

- **テスト計画に“期限切れclaimの再claim”を直接検証するケースを追加推奨です。**  
  `test_dedup_ttl_expiry.py` だけだと archive移動確認に寄りがちなので、  
  `claim → finalizeなし → TTL経過 → 再claim成功`  
  を明示的に確認するテストがあると、上記必須修正の実装担保になります。
