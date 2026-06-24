# SPEC v2.10.1 patch - cost_guard_v2 ゲート②NG 修正仕様

最終更新: 2026-06-17 / バージョン: v2.10.1 (patch on v2.10)
位置づけ: SPEC v2.10 で実装完了 → ゲート② NG → この patch で修正

---

## 0. 背景

ゲート②(GPT-5.4 コードレビュー)で以下の致命的問題が指摘された:
1. Cursor が独自追加した冪等性チェック(`_record_in_tx`/`_confirm_dedup_in_tx`/`_release_dedup_in_tx` の `row is None -> no-op`)が**サイレントなデータ破損リスク**
2. `log_event()` が BEGIN IMMEDIATE を使っていない(SPEC §8.3 違反)
3. `stopped_budget` 時の log_event.detail が空文字(SPEC §7.3.1 違反)
4. finalize 完了状態の表現が success/permanent しかカバーできず transient 冪等性が破綻
5. STATE_MISMATCH ログを tx 内記録すると rollback で消える
6. `claim_id is None`(装置3 skip)経路で誤判定リスク

これらを v2.10.1 patch として修正する。

---

## 1. 新規 enum / dataclass

### 1.1 FinalizeStatus enum

```python
from enum import Enum

class FinalizeStatus(str, Enum):
    OK_RECORDED    = "ok_recorded"      # success/permanent finalize 完了(record + confirm)
    OK_RELEASED    = "ok_released"      # transient finalize 完了(release + release_dedup)
    IDEMPOTENT     = "idempotent"       # 既に完了済みの再呼び出し
    STATE_MISMATCH = "state_mismatch"   # 不整合検出(ROLLBACK 済み、別tx で event_log 記録)
```

### 1.2 FinalizeResult dataclass

```python
from dataclasses import dataclass

@dataclass
class FinalizeResult:
    status: FinalizeStatus
    detail: str = ""   # state_mismatch 時は詳細理由
```

`finalize()` の戻り値型を `None` から `FinalizeResult` に変更する。

### 1.3 FinalizeState dataclass

```python
@dataclass
class FinalizeState:
    reservation_exists: bool        # reservations 行が存在するか
    reservation_finalized: bool     # reservations.finalized=1 か
    claim_exists: bool              # claim_id=None なら True 固定(skip扱い)
    claim_confirmed: bool           # claim_id=None なら True 固定 / 値 ! = 0 で True
```

**重要**: `claim_id=None`(装置3 skip)時は `claim_exists=True, claim_confirmed=True` で初期化する。これにより `has_claim` 分岐を上位で意識せず判定式が単純化できる。**ただし実装の保守性のため、上位 finalize() コードでも明示的に `has_claim = decision.claim_id is not None` で分岐する**(GPT-5.4 ゲート②round3 指摘)。

### 1.4 StateMismatchError 例外

```python
class StateMismatchError(Exception):
    """finalize の事前整合チェックで不整合検出時に内部的に raise。
    finalize() 内で捕捉し、外部には FinalizeResult(STATE_MISMATCH) で返す。"""
    pass
```

---

## 2. `_load_finalize_state_in_tx(conn, reservation_id, claim_id)` 新設

```python
def _load_finalize_state_in_tx(conn, reservation_id: str, claim_id: str | None) -> FinalizeState:
    """tx 内で reservation/claim の状態をスナップショット取得する。"""
    # reservation 側
    res_row = conn.execute(
        "SELECT finalized FROM reservations WHERE reservation_id=?",
        (reservation_id,)
    ).fetchone()
    res_exists = res_row is not None
    res_finalized = res_exists and res_row["finalized"] == 1

    # claim 側(claim_id=None なら skip 扱いで True 固定)
    if claim_id is None:
        return FinalizeState(
            reservation_exists=res_exists,
            reservation_finalized=res_finalized,
            claim_exists=True,
            claim_confirmed=True,
        )

    claim_row = conn.execute(
        "SELECT confirmed FROM dedup_claims WHERE claim_id=?",
        (claim_id,)
    ).fetchone()
    claim_exists = claim_row is not None
    claim_confirmed = claim_exists and claim_row["confirmed"] != 0  # ※ != 0(== 1 ではない、§3 参照)

    return FinalizeState(
        reservation_exists=res_exists,
        reservation_finalized=res_finalized,
        claim_exists=claim_exists,
        claim_confirmed=claim_confirmed,
    )
```

---

## 3. dedup_claims の error 列に 「2 = released(transient)」マーカー追加

### 3.1 release_dedup を DELETE から UPDATE に変更

```python
def _release_dedup_in_tx(conn, claim_id: str):
    """transient release: dedup_claims 行を残しつつ released マーカーをセット。"""
    row = conn.execute(
        "SELECT confirmed FROM dedup_claims WHERE claim_id=?",
        (claim_id,)
    ).fetchone()
    if row is None:
        raise StateMismatchError(f"claim not found in release: {claim_id}")
    if row["confirmed"] != 0:
        # 既に確定/解放済み → finalize() 側で IDEMPOTENT 判定されるはず、ここでは raise
        raise StateMismatchError(f"claim already finalized: {claim_id}")
    conn.execute(
        "UPDATE dedup_claims SET confirmed=1, error=2 WHERE claim_id=?",
        (claim_id,)
    )
```

### 3.2 error 列の意味(規約化)

| error 値 | 意味 |
|---|---|
| 0 | success 確定(record + confirm_dedup) |
| 1 | permanent failure 確定(record(error=True) + confirm_dedup(error=True)) |
| 2 | released(transient): release_dedup で完了マーキング |

### 3.3 archive cron の対象条件

- archive 対象: `confirmed=1 AND error IN (0, 1)` のみ(success/permanent failure の履歴)
- `error=2`(released) は別途 purge(週次 or 月次、運用判断)
- `confirmed=0`(未確定)は inline purge で TTL 超過時に削除済み

### 3.4 inline purge への影響

既存 SPEC §5.3 inline purge は `confirmed=0 AND first_seen <= now - ttl_sec` を対象とする。`confirmed=1, error=2` は purge 対象外。変更なし。

---

## 4. `_record_in_tx()` / `_confirm_dedup_in_tx()` の厳密化

### 4.1 `_record_in_tx()`

```python
def _record_in_tx(conn, reservation_id: str, in_tokens: int, out_tokens: int,
                  model: str, script: str, error: bool = False, **kwargs):
    row = conn.execute(
        "SELECT finalized FROM reservations WHERE reservation_id=?",
        (reservation_id,)
    ).fetchone()
    if row is None:
        raise StateMismatchError(f"reservation not found: {reservation_id}")
    if row["finalized"] == 1:
        # finalize() 側で IDEMPOTENT 判定されているはず、ここに来たら state mismatch
        raise StateMismatchError(f"reservation already finalized: {reservation_id}")
    # 通常処理: phase_calls.reserved -= 1, consumed += 1, reservations.finalized=1, ledger 行 INSERT
    ...
```

**Cursor が独自に追加した `row is None -> no-op` は廃止**。

### 4.2 `_confirm_dedup_in_tx()`

```python
def _confirm_dedup_in_tx(conn, claim_id: str, error: bool = False):
    row = conn.execute(
        "SELECT confirmed FROM dedup_claims WHERE claim_id=?",
        (claim_id,)
    ).fetchone()
    if row is None:
        raise StateMismatchError(f"claim not found: {claim_id}")
    if row["confirmed"] != 0:
        raise StateMismatchError(f"claim already finalized: {claim_id}")
    conn.execute(
        "UPDATE dedup_claims SET confirmed=1, error=? WHERE claim_id=?",
        (1 if error else 0, claim_id)
    )
```

### 4.3 `_release_in_tx()`

```python
def _release_in_tx(conn, reservation_id: str):
    row = conn.execute(
        "SELECT finalized FROM reservations WHERE reservation_id=?",
        (reservation_id,)
    ).fetchone()
    if row is None:
        raise StateMismatchError(f"reservation not found in release: {reservation_id}")
    if row["finalized"] == 1:
        raise StateMismatchError(f"reservation already finalized: {reservation_id}")
    # phase_calls.reserved -= 1, reservations.finalized=1(consumed は加算しない)
    ...
```

---

## 5. `log_event()` を tx 内外で分離

### 5.1 内部版 `_log_event_in_tx(conn, ...)` 新設

```python
def _log_event_in_tx(conn, reason: str, detail: str = "",
                     phase: str = "", block_type: str = "", script: str = ""):
    """tx 内文脈専用。外側の conn をそのまま使い、新たに BEGIN を取らない。"""
    conn.execute(
        "INSERT INTO event_log(timestamp, reason, detail, phase, block_type, script) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), reason, detail, phase, block_type, script)
    )
```

### 5.2 public 版 `log_event(...)` を BEGIN IMMEDIATE 化

```python
def log_event(reason: str, detail: str = "",
              phase: str = "", block_type: str = "", script: str = ""):
    """非 tx 文脈専用。自前で BEGIN IMMEDIATE を取得する。"""
    with state_store.begin_immediate() as conn:
        _log_event_in_tx(conn, reason, detail, phase, block_type, script)
```

### 5.3 既存呼び出し側の置換

`allowed()` / `finalize()` の tx 内からは **必ず `_log_event_in_tx(conn, ...)` を使う**。`log_event()` を tx 内から呼ぶと別 connection で BEGIN IMMEDIATE を取りに行き、self-deadlock/busy 待ちが発生する。

---

## 6. `finalize()` の完成形

```python
def finalize(decision: Decision, in_tokens: int = 0, out_tokens: int = 0,
             success: bool = True, error_kind: str = "") -> FinalizeResult:
    # === 1. 引数バリデーション ===
    if not success and not error_kind:
        raise ValueError("error_kind required when success=False")
    if success and error_kind:
        raise ValueError("error_kind must be empty when success=True")
    
    has_claim = decision.claim_id is not None
    is_mismatch = False
    mismatch_detail = ""
    
    # === 2. 単一 BEGIN IMMEDIATE トランザクション ===
    with state_store.begin_immediate() as conn:
        try:
            state = _load_finalize_state_in_tx(conn, decision.reservation_id, decision.claim_id)
            
            # --- 2.1 IDEMPOTENT 判定(claim 有無で分岐) ---
            if has_claim:
                if state.reservation_finalized and state.claim_confirmed:
                    return FinalizeResult(status=FinalizeStatus.IDEMPOTENT)
            else:
                if state.reservation_finalized:
                    return FinalizeResult(status=FinalizeStatus.IDEMPOTENT)
            
            # --- 2.2 MISMATCH 判定 ---
            if not state.reservation_exists:
                is_mismatch = True
                mismatch_detail = "reservation_missing"
            elif has_claim and not state.claim_exists:
                is_mismatch = True
                mismatch_detail = "claim_missing"
            elif has_claim and state.reservation_finalized and not state.claim_confirmed:
                is_mismatch = True
                mismatch_detail = "partial_finalized_reservation_only"
            elif has_claim and not state.reservation_finalized and state.claim_confirmed:
                is_mismatch = True
                mismatch_detail = "partial_finalized_claim_only"
            
            if is_mismatch:
                conn.rollback()  # 明示。何も書いていないが意図を明確化
            else:
                # --- 2.3 通常 finalize 実行 ---
                if success:
                    _record_in_tx(conn, decision.reservation_id, in_tokens, out_tokens,
                                  decision.model, decision.script, error=False)
                    if has_claim:
                        _confirm_dedup_in_tx(conn, decision.claim_id, error=False)
                elif error_kind == "transient":
                    _release_in_tx(conn, decision.reservation_id)
                    if has_claim:
                        _release_dedup_in_tx(conn, decision.claim_id)
                else:  # permanent_*
                    _record_in_tx(conn, decision.reservation_id, in_tokens, out_tokens,
                                  decision.model, decision.script, error=True)
                    if has_claim:
                        _confirm_dedup_in_tx(conn, decision.claim_id, error=True)
        except StateMismatchError as e:
            conn.rollback()
            is_mismatch = True
            mismatch_detail = str(e)
    
    # === 3. tx を抜けた後、別 tx で log_event ===
    if is_mismatch:
        try:
            log_event(reason="error_internal",
                      detail=f"finalize_state_mismatch:{mismatch_detail}",
                      phase=decision.phase, block_type=decision.block_type,
                      script=decision.script)
        except Exception as log_exc:
            # ログ失敗で業務処理の戻り値まで壊さない
            import logging
            logging.exception("failed to persist finalize_state_mismatch log: %s", log_exc)
        return FinalizeResult(status=FinalizeStatus.STATE_MISMATCH, detail=mismatch_detail)
    
    # === 4. 成功時の status ===
    if success:
        return FinalizeResult(status=FinalizeStatus.OK_RECORDED)
    elif error_kind == "transient":
        return FinalizeResult(status=FinalizeStatus.OK_RELEASED)
    else:  # permanent_*
        return FinalizeResult(status=FinalizeStatus.OK_RECORDED)
```

---

## 7. `allowed()` の stopped_budget 強化

### 7.1 同一 tx 内で daily/monthly を SELECT して detail を組み立てる

```python
# stopped_budget 分岐
with state_store.begin_immediate() as conn:
    ledger._release_in_tx(conn, reservation_id)
    if claim_id:
        ledger._release_dedup_in_tx(conn, claim_id)
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")
    daily_row = conn.execute("SELECT daily_usd FROM daily_state WHERE date=?", (today,)).fetchone()
    monthly_row = conn.execute("SELECT monthly_usd FROM monthly_state WHERE month=?", (month,)).fetchone()
    daily = daily_row["daily_usd"] if daily_row else 0.0
    monthly = monthly_row["monthly_usd"] if monthly_row else 0.0
    detail_str = f"daily_usd={daily:.4f}, monthly_usd={monthly:.4f}"
    ledger._log_event_in_tx(conn, reason="stopped_budget", detail=detail_str,
                            phase=phase, block_type=block_type, script=script)
return Decision(allowed=False, reason="stopped_budget", ...,
                detail=detail_str)
```

### 7.2 他の log_event 呼び出しも内部版に置換

`allowed()` 内の全 log_event 呼び出しを `_log_event_in_tx(conn, ...)` に変更。

---

## 8. テスト追加(11 本、Phase 8.24〜8.34)

| # | テスト名 | 検証内容 |
|---|---|---|
| 8.24 | test_finalize_transient_idempotent.py | transient finalize 再実行が IDEMPOTENT を返す |
| 8.25 | test_finalize_claim_none_idempotent.py | claim_id=None で success/permanent/transient 各々 idempotent |
| 8.26 | test_finalize_permanent_idempotent.py | permanent 再実行が IDEMPOTENT を返す |
| 8.27 | test_finalize_state_mismatch_returns_status.py | reservation 不在/claim 不在/片肺で STATE_MISMATCH 返却 |
| 8.28 | test_finalize_state_mismatch_logs_persist_after_rollback.py | mismatch ログが rollback 後の別 tx で永続化されることを検証(致命点) |
| 8.29 | test_log_event_in_tx_no_lock.py | allowed() の stopped_budget で lock 起きない |
| 8.30 | test_release_dedup_marker.py | release_dedup が confirmed=1/error=2 マーカーで完了表現 |
| 8.31 | test_archive_skips_released.py | archive cron が error=2 をスキップ |
| 8.32 | test_finalize_returns_finalize_result.py | 返り値型 FinalizeResult の検証 |
| 8.33 | test_finalize_claim_none_normal_no_mismatch.py | claim_id=None の正常 finalize 完了が mismatch にならない(誤判定防止) |
| 8.34 | test_finalize_log_event_failure_handled.py | log_event 失敗時でも FinalizeResult(STATE_MISMATCH) は返る |

---

## 9. 既存テスト23本(72ケース)への影響

以下のテストは v2.10.1 で期待値更新が必要:
- **test_finalize_idempotent.py**: success 経路の idempotent が `None` → `FinalizeResult(IDEMPOTENT)` に変更。assertion 修正
- **test_finalize_atomicity.py**: ROLLBACK 検証で `FinalizeResult(STATE_MISMATCH)` を確認、ログ永続化を別 tx で確認
- **test_finalize_permanent_kinds.py**: 戻り値型 FinalizeResult 期待値に更新
- **test_dedup_claim_transient_release.py**: claim 行が `confirmed=1, error=2` で残ることを確認(削除されない期待値に変更)
- **test_dedup_claim*.py**: archive 条件を `confirmed=1 AND error IN (0,1)` に揃える

---

## 10. ロールバック手順(緊急時)

万一 v2.10.1 patch 適用後に重大障害が発生した場合:
1. `git revert <patch commit>` で v2.10 状態に戻す
2. sqlite はそのまま(`state.sqlite3`)継続使用可能(schema 変更なし、データ非破壊)
3. ただし `error=2` マーカー付き行は `confirmed=1` 扱いになり archive 対象に入る → 軽微な不整合だが致命的ではない

---

## 11. 変更履歴

| 日付 | バージョン | 内容 |
|---|---|---|
| 2026-06-17 | v2.10.1 | ゲート②NG修正: Cursor 独自冪等性ロジック廃止 / FinalizeStatus/FinalizeResult/FinalizeState 導入 / _load_finalize_state_in_tx 新設 / release_dedup を DELETE→UPDATE(error=2 marker) / log_event 内部版分離 / claim_id=None 経路の明示分岐 / mismatch ログを rollback 後別 tx で永続化 / テスト11本追加 |
