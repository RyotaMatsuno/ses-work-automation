# Phase4 SPEC: mail_pipeline 改修

## 変更1: dedupキーの安定化（Message-ID無しメールの再処理問題を解消）

`fetch_emails_from_account()` の L406付近:
```python
# 変更前
msg_id = msg.get("Message-ID", f"no-id-{mail_id.decode()}-{user}")

# 変更後
import hashlib
_raw_id = msg.get("Message-ID", "")
if _raw_id:
    msg_id = _raw_id
else:
    # IMAP連番は不安定なのでFrom+Subject+Date+本文先頭のハッシュを使う
    _dedup_src = f"{msg.get('From','')}|{msg.get('Subject','')}|{msg.get('Date','')}|{body[:100]}"
    msg_id = "hash-" + hashlib.sha1(_dedup_src.encode("utf-8", errors="replace")).hexdigest()[:16]
```

## 変更2: call_claude()のコストゲートをledger接続に変更

`call_claude()` 関数（L466付近）の変更:

ファイル先頭に追加（importセクション）:
```python
import sys as _sys, os as _os
_sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from common.ledger import can_spend as _ledger_can_spend, record as _ledger_record
    _LEDGER_OK = True
except ImportError:
    _LEDGER_OK = False
```

`call_claude()` 冒頭の既存ガードを置き換え:
```python
def call_claude(system: str, user: str, max_tokens: int = 1500) -> str:
    # グローバルコストゲート
    if _LEDGER_OK:
        if not _ledger_can_spend(len(user)//4 + 300, max_tokens, "claude-haiku-4-5-20251001"):
            log("[LEDGER] グローバルコスト上限によりAPIスキップ")
            return ""
    elif get_today_cost_usd() >= DAILY_COST_LIMIT_USD:  # fallback
        log(f"[COSTFIX] 日次コスト上限 ${DAILY_COST_LIMIT_USD} に達したためAPIコールをスキップ")
        return ""
    # ... 以降既存コード ...
```

API成功後、既存の`log_cost()`呼び出しの後に追加:
```python
if _LEDGER_OK:
    _ledger_record(
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
        data.get("model") or "claude-haiku-4-5-20251001",
        "mail_pipeline"
    )
```

## 変更3: Batch分類のコスト記録（send_batch結果からusage取得）

`classify_email_v2()` 内の `send_batch()` ヘルパー関数の戻り値処理後に追加:

`send_batch()` が返すresult items処理ループ（L678付近）でbatch結果を処理する箇所で、
各itemの`result.message.usage`を集計してledger.record()する:

```python
# send_batch(batch_requests) の直後、for item in ... のループ内
for item in send_batch(batch_requests):
    custom_id = item.get("custom_id", "")
    text = result_text(item)
    parsed = parse_json_text(text)
    # コスト記録（新規追加）
    if _LEDGER_OK:
        _usage = item.get("result", {}).get("message", {}).get("usage", {})
        if _usage:
            _ledger_record(
                _usage.get("input_tokens", 0),
                _usage.get("output_tokens", 0),
                "claude-haiku-4-5-20251001",
                "mail_pipeline_batch"
            )
    # ... 既存のcustom_id判定ロジックを続ける ...
```

同様に send_batch(second_extract_requests) の結果処理ループにも同じ記録を追加。

## 変更4: ai_matching を ledger ゲートに通す

`ai_matching()` 関数内（L727付近）で `call_claude` を呼ぶ前に既にコストゲートがある（call_claude内部）。
追加変更なし（call_cloudueが既にledger接続されるため自動でゲートされる）。

## 完了確認
- dedupキーに "hash-" プレフィックスのパターンが存在する
- call_claude() に _ledger_can_spend の呼び出しがある
- call_claude() に _ledger_record の呼び出しがある  
- send_batch 結果処理に _ledger_record の呼び出しがある
- py_compile が通る
