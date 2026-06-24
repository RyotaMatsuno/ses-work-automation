# stopped_budget except 修正方針レビュー

日時: 2026-06-17T16:04:02.264822
model: gpt-5.4
usage: {"prompt_tokens": 1001, "completion_tokens": 1405, "total_tokens": 2406, "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 166, "audio_tokens": 0, "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0}}

---

【追加修正必要】

結論: 提案方針は**半分正しいが不十分**です。  
`except Exception` の握り潰しを弱める意図は良いですが、**cleanup と detail取得/ログ記録が同じ try に入ったまま**なので、3問題を確実には潰せません。

## 1. 3問題は解消するか

### 予約リーク
**未解消の可能性あり**です。  
理由は、cleanup失敗を `sqlite3.OperationalError, StateMismatchError` に限定しているためです。  
`_release_in_tx()` / `_release_dedup_in_tx()` がそれ以外の例外を投げた場合、下の `except Exception as e:` に入り、**stopped_budget で返してしまう**ため、リークを再び握り潰します。

### detail空文字再発
**かなり改善するが、完全ではない**です。  
少なくとも `detail_str = ""` 固定ではなくなるので再発しにくいです。  
ただし `_notify(...)` 側や `_fail_decision(...)` 側で detail を落とす実装だと別途再発余地はあります。  
この修正箇所単体では概ね改善です。

### 誤分類
**未解消の可能性あり**です。  
cleanup失敗なのに、例外型が想定外だと `stopped_budget` に分類されます。  
したがって「cleanup失敗は error_internal」という設計意図を満たし切れていません。

---

## 2. `sqlite3.OperationalError` と `StateMismatchError` 以外に cleanup失敗要因はあるか

**あります。** 少なくとも以下は候補です。

- `sqlite3.IntegrityError`
- `sqlite3.DatabaseError`
- `sqlite3.ProgrammingError`
- `sqlite3.InterfaceError`
- `sqlite3.Error` 全般
- `_release_in_tx()` / `_release_dedup_in_tx()` 内の独自例外
- 型不整合由来の `TypeError`, `ValueError`
- 接続/カーソル状態異常由来の `RuntimeError`

なので、**例外型の列挙で cleanup失敗を見分ける設計は危うい**です。  
**try を分割して、「どこで失敗したか」で分類する**方が安全です。

---

## 3. 「軽微エラー」分岐で stopped_budget を返す判断は妥当か

**cleanup成功が保証できるなら妥当**です。  
ただし現提案では保証できていません。  
同じ try の中で cleanup → 残高取得 → イベント記録をやっているため、`except Exception as e:` に入った時点で、

- cleanupは成功済み
- cleanupで失敗した
- detail取得で失敗した
- stopped_budgetログ記録で失敗した

の区別がつきません。

したがって、妥当化するには**構造変更が必要**です。例えば:

```python
detail_str = ""

# 1) cleanup は単独で必達判定
try:
    with begin_immediate() as conn:
        _release_in_tx(conn, reservation_id)
        if claim_id:
            _release_dedup_in_tx(conn, claim_id)
except Exception as e:
    msg = f"budget_cleanup_error:{e}"
    _log(Reasons.error_internal, msg)
    return _fail_decision(
        Reasons.error_internal, 2,
        script=script, phase=phase, block_type=block_type, detail=msg,
    )

# 2) detail取得・stopped_budget記録はベストエフォート
try:
    with begin_immediate() as conn:
        ...
        detail_str = ...
        _log_event_in_tx(...)
except Exception as e:
    detail_str = f"budget_stop_with_partial_error:{e}"

_notify(Reasons.stopped_budget, detail_str)
return Decision(... detail=detail_str)
```

これなら  
- cleanup失敗 → `error_internal`
- cleanup成功後の付随処理失敗 → `stopped_budget`
が明確になります。

---

## 4. 既存テスト116本への影響はないか

**「影響なし」とは言えません。**  
理由:

- cleanup失敗時の戻り値が `stopped_budget` → `error_internal` に変わる
- `detail=""` 前提のテストがあれば落ちる
- ログ出力内容を見ているテストがあれば落ちる
- `_notify()` が呼ばれない/呼ばれ方が変わるケースが出る可能性がある

特に今回の修正は**障害時の分類変更**を含むため、通常系テストは大きく壊れにくい一方、異常系・モック系は影響あり得ます。  
**回帰確認は必要**です。

---

## 推奨

- **例外型で cleanup失敗を判定しない**
- **cleanup と detail取得/ログ記録を try 分離する**
- cleanup失敗時は **必ず `error_internal` + detailあり**
- ベストエフォート失敗時も **detailは空にしない**

要するに、**提案の方向性は良いが、そのままでは再発防止として弱い**です。
