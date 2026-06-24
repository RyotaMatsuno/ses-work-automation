# ゲート② 再々レビュー(cost_guard v2.10.1 final)

日時: 2026-06-17T16:12:38.311796
model: gpt-5.4
usage: {"prompt_tokens": 12177, "completion_tokens": 1514, "total_tokens": 13691, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 330, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【GO】

前回NG理由は解消されています。明朝8時の自動実行に向けて、本番デプロイ継続可と判断します。

### 1. 前回NG理由の解消確認
`allowed()` の `stopped_budget` 分岐は、指摘どおり **cleanup** と **detail取得/ログ** が明確に try 分離されています。

#### 現状の挙動
1. **cleanup 専用 try**
   - `begin_immediate()` の単独 tx 内で
     - `_release_in_tx(conn, reservation_id)`
     - `claim_id is not None` のとき `_release_dedup_in_tx(conn, claim_id)`
   - 失敗時は `Reasons.error_internal` で即 return

2. **detail取得・ログのベストエフォート try**
   - 別 tx で `daily_state` / `monthly_state` を読んで
   - `detail_str = f"daily_usd=..., monthly_usd=..."`
   - `_log_event_in_tx(...)`
   - 失敗時は `detail_str = "budget_stop_with_partial_error:..."`

この構造により、前回の問題だった
- `except Exception` による cleanup失敗の握り潰し
- 予約/claimのリーク見逃し
- `detail=""` の再発
- `stopped_budget` への誤分類

は解消されています。

---

### 2. cleanup失敗時の扱い
要件どおり、cleanup失敗時は以下になります。

```python
except Exception as e:
    msg = f"budget_cleanup_error:{e}"
    _log(Reasons.error_internal, msg)
    return _fail_decision(Reasons.error_internal, 2, ...)
```

これは適切です。

#### 評価
- **予約リークを“隠したまま stopped_budget で返す”挙動はなくなった**
- cleanup失敗を **業務上の内部異常として正しく表面化** している
- 少なくとも前回の致命点である「リーク + 空detail + 誤分類」は防げています

厳密には、cleanup自体がDB障害等で失敗した場合、物理的なリーク可能性は残ります。  
ただし今回はその事実を **error_internal として返し、黙殺しない** ことが修正方針であり、そこは満たしています。

---

### 3. detail空文字の再発有無
`budget_ok == False` 時の `Decision.detail` は、現実的に空文字へ戻りません。

- cleanup成功後、detail取得成功なら  
  `daily_usd=..., monthly_usd=...`
- detail取得/ログ失敗なら  
  `budget_stop_with_partial_error:...`

よって、前回問題だった **`stopped_budget` なのに detail が空** は再発していません。

---

### 4. finalize側の退行確認
今回の差分で、少なくとも提示コード範囲では前回解消済み事項への退行は見当たりません。

確認できた点:
- `FinalizeStatus` / `FinalizeResult` 導入済み
- `decision.allowed == False` なら `IDEMPOTENT` 返却
- `has_claim = decision.claim_id is not None` の明示分岐あり
- 単一 tx 内で `_load_finalize_state_in_tx(...)` による状態判定
- mismatch時は rollback 後に tx外で `log_event`
- transient は `OK_RELEASED`
- permanent/success は `OK_RECORDED`

このため、今回レビュー観点の範囲では **finalize側の退行なし** と見てよいです。

---

### 5. 軽微な推奨事項
いずれも **GOを覆すものではありません**。

#### 推奨1: `stopped_budget` 返却時の `reservation_id` / `claim_id`
現在は cleanup済みでも返却値に
- `reservation_id=reservation_id`
- `claim_id=claim_id`

が残ります。

実害は薄いですが、呼び出し側が誤って `allowed=False` の Decision を `finalize()` に流すような実装だと、将来的な誤解の元にはなりえます。  
ただし `finalize()` は `if not decision.allowed: IDEMPOTENT` なので、**今すぐの本番阻害要因ではありません**。

#### 推奨2: `datetime.now()` のタイムゾーン統一
`stopped_budget` detail取得部で `datetime.now().strftime(...)` を使っていますが、他所では JST / UTC を意識しています。  
ここは将来的には統一推奨です。もっとも、DBの日付キー運用がローカル時刻前提なら現時点で致命ではありません。

---

### 最終判断
- 前回NG理由は **解消済み**
- 修正方針どおりの実装になっている
- 本番投入を止める致命的不備は、提示コード上は見当たりません

**結論: GO**
