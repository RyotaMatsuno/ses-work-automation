# ゲート② 再レビュー(cost_guard v2.10.1 patch)

日時: 2026-06-17T16:01:00.994621
model: gpt-5.4 (reasoning_effort=low, max_completion_tokens=8000)
usage: {"prompt_tokens": 19028, "completion_tokens": 3057, "total_tokens": 22085, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 749, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}
対象ファイル: ['cost_guard.py', 'common/ledger.py', 'common/dedup.py', 'common/state_store.py', 'cost_guard_v2/SPEC_v2.10.1_patch.md']

---

【NG】

**修正必須項目**
- `allowed()` の `stopped_budget` 分岐で、`begin_immediate()` 内の解放・詳細取得・`_log_event_in_tx()` を **丸ごと `except Exception: detail_str = ""` で握り潰している**ため、前回NG指摘 **#3「stopped_budget の detail が空文字」** が**異常系で未解消**です。  
  しかもこの例外時は `reservation` / `dedup claim` の解放失敗も隠蔽され、`allowed=False` を返して `finalize()` も呼ばれないため、**予約リーク・claimリーク**を起こします。これは本番でじわじわ詰まる系の障害です。
- 上記に関連して、`stopped_budget` cleanup 失敗時の戻り値/ログ方針を明確化してください。現状は cleanup 失敗でも `stopped_budget` を返すため、**実際は内部不整合なのに予算停止として誤分類**されます。少なくとも cleanup 失敗時は `error_internal` 相当で返す、または mismatch 扱いにして別 tx で永続ログすべきです。

**推奨項目**
- `allowed()` の `stopped_budget` 分岐でも `has_claim = claim_id is not None` を使って条件統一すると、`if claim_id:` より保守性が上がります。
- `finalize()` は `begin_immediate()` を使わず手動 `open_conn()+BEGIN IMMEDIATE` ですが、実装自体は成立しています。共通化すると保守しやすいです。
- `record()` の `_append_log()` は DB commit 後の別系統で失敗黙殺ですが、監査要件が強いなら warning は残した方がよいです。

---

## 1. 前回NG指摘6点は全て解消されているか

**5/6 は解消、1点は未解消です。**

### 1. `_xxx_in_tx` の `row is None -> no-op`
**解消済み。**  
`_record_in_tx()` / `_release_in_tx()` / `_confirm_dedup_in_tx()` / `_release_dedup_in_tx()` で、`row is None` や二重確定時に `StateMismatchError` を raise する実装になっています。  
前回のサイレント破損リスクは潰れています。

### 2. `log_event()` が `BEGIN IMMEDIATE` 未使用
**解消済み。**  
`common.state_store.begin_immediate()` を使う public `log_event()` と、tx 内専用 `_log_event_in_tx()` に分離されています。良い修正です。

### 3. `stopped_budget` の `detail` が空文字
**未解消（異常系で再発）。**  
正常系では
```python
detail_str = f"daily_usd={daily:.4f}, monthly_usd={monthly:.4f}"
_log_event_in_tx(...)
```
となっており改善されています。  
しかし実際のコードは:
```python
        except Exception:
            detail_str = ""
```
で全例外握り潰しです。  
このため lock / mismatch / release失敗 / log失敗 などで **また空文字に戻ります**。前回指摘の本質は「必ず原因が追えること」なので、ここは未達です。

### 4. transient finalize の冪等性破綻
**解消済み。**  
`release_dedup` が DELETE ではなく `confirmed=1, error=2` マーカー更新になり、`_load_finalize_state_in_tx()` が `confirmed != 0` を finalized 扱いするため、transient の再 finalize は `IDEMPOTENT` になります。ここは仕様通りです。

### 5. `STATE_MISMATCH` ログが rollback で消える
**解消済み。**  
`finalize()` で rollback 後に別 tx の `_log_event(...)` を呼んでおり、消えません。ここは前回指摘に対して適切です。

### 6. `claim_id=None` 経路の誤判定リスク
**概ね解消済み。**  
`has_claim = decision.claim_id is not None` を明示し、`_load_finalize_state_in_tx()` 側でも `claim_id is None` を `claim_exists=True, claim_confirmed=True` として返しているため、誤って mismatch 判定に寄るリスクはかなり下がっています。  
`finalize()` の主要分岐も `has_claim` で正しくガードされています。

---

## 2. finalize の原子性 + 冪等性 + mismatch 検出は正しく実装されているか

**はい、`finalize()` 自体はかなり良いです。**

### 原子性
- 単一 connection
- `BEGIN IMMEDIATE`
- 状態読取 → 判定 → record/release/confirm を同一 tx で実施
- mismatch 時は rollback
- mismatch ログのみ tx 外で別永続化

この構成は適切です。

### 冪等性
- `decision.allowed == False` は即 `IDEMPOTENT`
- `has_claim=True` では `reservation_finalized and claim_confirmed`
- `has_claim=False` では `reservation_finalized`

この分岐で success / permanent / transient の再呼び出しを吸収できています。  
特に transient が `error=2` マーカーで表現されるようになった点が効いています。

### mismatch 検出
- `reservation_missing`
- `claim_missing`
- `partial_finalized_reservation_only`
- `partial_finalized_claim_only`
- 内部関数からの `StateMismatchError`

これらを `FinalizeResult(STATE_MISMATCH, detail=...)` に集約しており、レビュー観点としては十分です。

---

## 3. `claim_id=None` 経路で誤判定は起きないか

**`finalize()` に限れば、現実的には起きにくい実装です。**

根拠:
- `has_claim = decision.claim_id is not None` が明示されている
- `_load_finalize_state_in_tx(..., claim_id=None)` は `claim_exists=True, claim_confirmed=True`
- mismatch 条件も `has_claim` 付きで判定している
- success/permanent/transient いずれも claim 操作は `has_claim` でガード

したがって、前回懸念だった「claim が無いのに claim 不整合扱いされる」系は解消されています。

ただし `allowed()` 側の budget-stop cleanup ではまだ
```python
if claim_id:
    _release_dedup_in_tx(conn, claim_id)
```
となっているので、設計の統一性としては `is not None` に寄せた方が安全です。  
実害は現状ほぼありませんが、レビューとしては統一推奨です。

---

## 4. 本番デプロイ継続して良いか

**現状のままは非推奨です。NG判定です。**

理由は1点に集約されます。

### NGの本質
`allowed()` の `stopped_budget` 分岐で cleanup/log 例外を握り潰して `stopped_budget` を返してしまうため、
- `detail` 空文字が再発
- `reservation` 未解放
- `dedup claim` 未解放
- 真因が `error_internal` / lock / mismatch でも `stopped_budget` に誤分類

となります。  
これは**前回指摘 #3 の再発**であるだけでなく、**運用上は呼び出し枠リークによる詰まり**を起こし得るので、朝8時自動実行前に潰す価値があります。

---

## 最短の修正方針

`allowed()` の budget NG 部分を、少なくとも次のようにしてください。

- cleanup / detail取得 / event_log 永続化に失敗したら握り潰さない
- `sqlite3.OperationalError` や `StateMismatchError` は `error_internal` で返す
- どうしても `stopped_budget` を返すなら、**解放成功後のみ**に限定する

イメージ:
```python
    if not budget_ok:
        try:
            with begin_immediate() as conn:
                _release_in_tx(conn, reservation_id)
                if claim_id is not None:
                    _release_dedup_in_tx(conn, claim_id)

                ...
                detail_str = f"daily_usd={daily:.4f}, monthly_usd={monthly:.4f}"
                _log_event_in_tx(conn, Reasons.stopped_budget, detail_str, ...)
        except _sqlite3.OperationalError:
            _log(Reasons.error_internal, "lock_timeout")
            return _fail_decision(Reasons.error_internal, 2, ..., detail="lock_timeout")
        except StateMismatchError as e:
            _log(Reasons.error_internal, f"budget_cleanup_mismatch:{e}")
            return _fail_decision(Reasons.error_internal, 2, ..., detail=str(e))

        _notify(Reasons.stopped_budget, detail_str)
        return Decision(... detail=detail_str)
```

---

## 結論

- **質問1:** 6点すべて解消か → **いいえ。#3 が異常系で未解消**
- **質問2:** `finalize` の原子性/冪等性/mismatch → **概ね正しく実装**
- **質問3:** `claim_id=None` 誤判定 → **`finalize()` では問題ない**
- **質問4:** 本番継続可否 → **現状は NG**

必要なら次に、**「朝8時までに入れる最小修正diff」** の形で修正案を出します。
