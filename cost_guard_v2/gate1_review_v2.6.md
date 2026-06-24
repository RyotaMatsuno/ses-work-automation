# ゲート① レビュー(SPEC v2.6)

日時: 2026-06-16T18:37:00.502387
model: gpt-5.4
usage: {"prompt_tokens": 7669, "completion_tokens": 1742, "total_tokens": 9411, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 704, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

## 前回(v2.5)必須指摘の解消状況

- ⚠ **dedup claim TTL の実効TTL化は本文レベルではほぼ解消。ただしテスト計画に旧仕様由来の矛盾が残っています。**  
  §5.3 は前回指摘どおり、
  - `claim_dedup()` 内で
  - `confirmed=0 AND first_seen <= now - ttl_sec`
  を inline purge した上で INSERT する仕様に書き換わっており、**「TTL経過後は週次cron待ち不要で再claim可能」** も明記されています。  
  また archive も **`confirmed=1` のみ** と整理され、前回の本文衝突は解消方向です。

  ただし §14 に
  - `test_dedup_ttl_expiry.py(TTL超過分が archive に移動)`
  
  が残っており、これは §5.3 の
  - **期限切れ未確定claimは inline purge で削除**
  - **archive 対象は confirmed=1 のみ**
  
  と整合しません。  
  仕様本文は直っていますが、**テスト計画が旧解釈のままだと実装・検証で再びぶれる**ため、完全解消とは言い切れません。

## 新たな必須修正項目

1. **§14 の `test_dedup_ttl_expiry.py(TTL超過分が archive に移動)` を修正してください。**  
   現仕様では、TTL超過で再claim可能になる対象は **未確定(`confirmed=0`) claim の inline purge** です。  
   よって「TTL超過分が archive に移動」は誤りです。少なくとも以下のどちらかに直す必要があります。
   - `confirmed=0` の期限切れclaimは `claim_dedup()` 実行時に purge され、archive されない
   - archive に移るのは週次cron時点の `confirmed=1` レコードのみ

   既に
   - `test_dedup_claim_ttl_inline_purge.py`
   - `test_dedup_claim_expired_reclaim.py`
   
   があるため、`test_dedup_ttl_expiry.py` は削除・改名・期待値修正のいずれかで整理するのが妥当です。

## 推奨項目

- **§7.1 の `Decision.reason` / `allowed()` docstring に「成功時は `reason="ok"` 固定」を実際の本文として追記してください。**  
  §0.2 と §16 では反映済みと読めますが、§7.1 のコードブロック内コメントと docstring にはまだ直接は見えません。実装者が最初に見る場所なので、明文化した方が安全です。

- **`finalize()` における `error_kind` → `reason enum` の対応表を1行でもよいので明記するとさらに堅くなります。**  
  例:
  - `permanent_auth -> error_auth`
  - `permanent_bad_request -> error_bad_request`
  - `permanent_response_invalid -> error_response_invalid`
  - `permanent_api -> error_permanent_api`  
  現状でも読み取れますが、§6・§7・§9 を跨いで補完する必要があります。

- **§5.3 の「再claimレコード側に履歴が残る」という説明は少し言い過ぎなので言い回しを補正すると誤解が減ります。**  
  inline purge された未確定claim自体は消えるため、厳密には「旧claimの履歴が残る」わけではありません。  
  例えば  
  「未確定期限切れclaimは監査保管せず削除し、再claim後の新レコードのみ現行テーブルに残る」  
  のように書くと正確です。

- **`error_internal.detail` の推奨値例を列挙すると運用しやすいです。**  
  例: `lock_timeout`, `sqlite_corrupt`, `schema_mismatch`, `migration_not_run`。  
  せっかく `ledger.record(... detail=...)` まで固定したので、値の粒度も軽く標準化すると障害切り分けが速くなります。
