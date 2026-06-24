# ゲート① レビュー(SPEC v2.7)

日時: 2026-06-16T21:58:22.653269
model: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 7579, "completion_tokens": 1983, "total_tokens": 9562, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 807, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【条件付きGO】

まず、前回 v2.6 レビュー時の **必須1件 + 推奨4件** については、**本文上は解消確認できました**。  
- §14 `test_dedup_ttl_expiry.py` 削除：解消
- §5.3 の「履歴が残る」表現修正：解消
- §7.1 docstring 補強（成功時 `reason="ok"` 固定 / `error_kind → reason` 対応表）：解消
- §9 `error_internal.detail` 推奨値例の列挙：解消
- §11.3 `ledger.record()` の `reason/detail` 利用明確化：解消

そのうえで、**今回の v2.7 は 1 件だけ実装上の致命的あいまいさが残るため、条件付きGO** とします。

## 修正必須項目
- **§3.2.1 / §11 系で、予約確定時の `phase_calls.reserved` 減算が仕様に明記されていません。**
  - 現仕様では
    - `reserve()` で `reserved += 1`
    - transient失敗時の `release()` で `reserved -= 1`
    - 成功 / permanent失敗時は `record(... reservation_id=...)` で `consumed += 1`
    までは読めますが、**成功 / permanent失敗時に `reserved -= 1` する記述がありません。**
  - このままだと `reserved` が積み上がり続け、`DAILY_CALL_LIMIT` 判定が `consumed + reserved` ベースなら**誤停止**、`reserved` 単独参照でも**予約リーク**になります。
  - 特に §8.4 で `phase_calls.reserved` を「真実源」と宣言しているため、ここは仕様未定義のまま実装に委ねてはいけません。
  - **修正案**
    - §3.2.1 を以下のように明文化してください。  
      - 成功 → `record(... reservation_id=...)` で **`reserved -= 1` かつ `consumed += 1`**
      - permanent失敗 → `record(... error=True, reservation_id=...)` で **`reserved -= 1` かつ `consumed += 1`**
      - transient失敗 → `release(reservation_id)` で **`reserved -= 1` のみ**
    - 併せて `reservations.finalized=1` をどのタイミングで立てるかも記載してください。

## 推奨項目
- **`Decision` の失敗時フィールド既定値を明記する**
  - `allowed()` は early exit が多く、`model` / `model_class` / `dedup_key` が未確定のまま失敗し得ます。
  - 現シグネチャは non-optional なので、**失敗時は空文字 `""` を返す**などを明記しておくと呼び出し側互換性が安定します。

- **`finalize()` の不正引数組み合わせを仕様化する**
  - 例: `success=False` かつ `error_kind=""`、`success=True` かつ `error_kind="transient"`。
  - 現在は docstring から期待値は推測できますが、**`error_internal` 扱いで拒否 / 自動補正 / assert** のどれかを決めた方が安全です。

- **`error_internal.detail` の保存先を `allowed()` 系失敗でも明確化する**
  - §11.2 では `ledger.record(... detail=...)` に寄せていますが、`allowed()` 段階の失敗は `record()` 前に終わるケースがあります。
  - ログのみなのか、別の障害イベント記録先を持つのかを補足すると運用しやすいです。

- **`BEGIN IMMEDIATE` のロック競合試験をテスト計画にもう1本足す**
  - `test_call_limit_race.py` と `test_dedup_claim_race.py` はありますが、**timeout 到達時に `reason=error_internal`, detail=`lock_timeout`** になることの明示テストがあると、§8.3 / §9 の結合確認になります。

- **`model_hint` の扱いを仕様化する**
  - `allowed()` シグネチャにあるのに本文で意味が定義されていません。
  - 無視するのか、優先候補にするのか、phase指定と矛盾時どうするのかを明記推奨です。

総評として、**v2.6 指摘の反映は確認でき、claim方式 + TTL inline purge の整合も取れています。**  
残る論点は **予約確定時の `reserved` 減算漏れ** だけで、ここを直せば **GO 相当** です。
