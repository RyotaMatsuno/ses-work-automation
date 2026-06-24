# ゲート① レビュー(SPEC v2.5)

日時: 2026-06-16T18:33:50.220627
model: gpt-5.4
usage: {"prompt_tokens": 7733, "completion_tokens": 1090, "total_tokens": 8823, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 167, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

## 前回(v2.4)必須指摘の解消状況

- ✅ **`target_id` 必須違反を `error_internal` から分離**  
  §0.2, §5.4, §6, §9, §10, §14 で `error_missing_target_id` へ分離されており、前回必須指摘は解消済みです。  
  reason enum・通知優先度・テスト計画まで追随していて、仕様の整合性も概ね取れています。

- ⚠ **dedup claim TTL の実効TTL化**  
  §0.2 と §14 では **`claim_dedup()` 内で期限切れ未確定claimを inline purge** する方針が明記されており、修正意図は正しいです。  
  ただし **§5.3 がなお旧説明のまま**で、  
  > 「TTL超過 → 週次cronで archive へ移動(再試行可能)」  
  と読めるため、本文内で仕様が衝突しています。  
  このままだと実装者によって  
  - claim時 inline purge を実装する  
  - 週次archive待ちのままにする  
  の両解釈が成立してしまいます。  
  前回問題の本質は「TTLが実効値にならないこと」なので、ここは **仕様本文を一本化するまで未解消扱い** が妥当です。

## 新たな必須修正項目

- **§5.3 の TTL 仕様を、inline purge 前提の実効TTLに明示的に書き換えてください。**  
  現状は §0.2 / §14 と §5.3 が矛盾しています。最低限、§5.3 を以下の趣旨に修正してください。  
  - `claim_dedup()` は同一トランザクション内で `confirmed=0` かつ `first_seen + ttl_sec < now` の期限切れclaimを purge してから INSERT を試行する  
  - したがって **TTL経過後は週次cronを待たず再claim可能**  
  - `dedup_claims_archive` への週次移動は「監査/保管用途」であり、再実行可否の真実源ではない  
  ここが曖昧なままだと、v2.4で指摘した運用上の再実行性問題が再発します。

## 推奨項目

- **`Decision.reason` 成功時 `"ok"` 固定を、§7.1 の `Decision`/`allowed()` 説明にも直接追記するとよいです。**  
  v2.5 の変更意図は §0.2, §16 から読めますが、実装者が最初に見る §7 に明記されている方がぶれません。

- **`claim_dedup()` の purge 条件を DB列ベースで具体化すると安全です。**  
  例えば  
  `confirmed=0 AND first_seen <= now - ttl_sec`  
  のように明文化すると、confirm済みclaimを誤って回収する解釈を防げます。

- **archive テーブルへ移す条件も補足すると保守しやすいです。**  
  期限切れ未確定claimを inline purge で削除するなら、週次archive対象が  
  - confirm済みレコードのみ  
  - もしくは purge前に退避したものも含む  
  のどちらかを明示した方が監査設計が安定します。

- **`error_internal.detail` の格納先を固定すると運用が楽です。**  
  §9 と §11.3 に意図はありますが、ledger / log / 通知のどこに必須記録するかを決めると切り分けがさらに容易です。
