# SPEC.md - Phase3: mail_pipeline再構築

## 変更1: dedupキー安定化
【場所】`fetch_emails_from_account()` 内 L406 付近

現在:
```python
msg_id = msg.get("Message-ID", f"no-id-{mail_id.decode()}-{user}")
```
↓ 変更後:
```python
import hashlib
_raw_id = msg.get("Message-ID", "")
if _raw_id:
    msg_id = _raw_id
else:
    _key = f"{msg.get('From','')}{msg.get('Subject','')}{msg.get('Date','')}{body[:100]}"
    msg_id = f"no-id-stable-{hashlib.sha1(_key.encode('utf-8','replace')).hexdigest()[:20]}"
```
※ hashlib は標準ライブラリ。ファイル先頭のimportにも追加する。
※ bodyはget_body_and_attachments()呼び出し後なので使える。呼び出し順序は変えない。

## 変更2: ai_matching() / extract_affiliation(LLM) / save_draft() をmain()から撤去

【場所】`main()` 内の projectメール処理ブロック（L1366付近 `if msg_type == "project":`）

現在のフロー:
```
register_project() → save_attachments_for_page() → filter_engineers_by_skills()
→ ai_matching() → save_draft() → send_proposal_email() → save_processed_id()
```

変更後のフロー:
```
# LLM呼び出し部分（extract_affiliation・ai_matching・save_draft・send_proposal_email）を全て削除
# affiliation は空文字列固定
# register_project() → save_attachments_for_page() → save_processed_id()
# ログに「matching_v3に委譲」と出力する
```

具体的な変更：
1. `affiliation = extract_affiliation(body)` → `affiliation = ""` に変更
2. `filtered = filter_engineers_by_skills(...)` の行とその後の `if not filtered: ...` ブロック全体を削除
3. `matching = ai_matching(...)` の行とその後の processing を削除
4. `if not candidates:` ブロックを削除
5. `save_draft(...)` 呼び出しを削除
6. `send_proposal_email(...)` 呼び出しを削除
7. 代わりに `log(f"  [OK] 案件登録完了: {proj_name} → matching_v3が次回マッチング")` を追加
8. `save_processed_id(msg_id, processed)` は残す（処理済みマーク必須）
9. `continue` も残す

注意:
- `get_available_engineers()` 呼び出し (L1344) も削除する（使わなくなる）
- engineer-related の変数参照エラーが起きないこと
- この変更によりprojectメールはNotion登録のみで完結する

## 変更3: Batch APIコストをledgerに記録

【場所】`classify_email_v2()` 内の `send_batch()` 関数

現在: send_batch は cost_log に記録しない

変更後:
- send_batch() 関数の return の直前で、batch結果のusageを集計してledger.record()を呼ぶ
- 各結果itemから `result.message.usage.input_tokens` / `output_tokens` を取得する:
```python
# send_batch return直前に追加
total_in = total_out = 0
for item in results:
    usage = item.get("result", {}).get("message", {}).get("usage", {})
    total_in  += int(usage.get("input_tokens", 0))
    total_out += int(usage.get("output_tokens", 0))
if total_in > 0 or total_out > 0:
    try:
        from common.ledger import record as _led_record
        _led_record(total_in, total_out, model, "mail_pipeline_batch")
    except Exception:
        pass
```
※ modelはsend_batch の外側スコープから参照できる（classify_email_v2 の `model` 変数）

## 変更4: スケジューラ設定スクリプト（新規）

`pf3_mailpipeline/setup_schedules.py` を作成・実行:

1. SES_MailPipeline を60分間隔に変更:
   `schtasks /Change /TN SES_MailPipeline /RI 60`

2. SES_MatchingV3 を1日4回（08:00/11:00/14:00/17:00）に変更:
   既存タスクを削除して再作成するより、まず現状確認してから
   XMLテンプレートで4トリガー設定が複雑なため、
   代替案として SES_MatchingV3 を2時間毎に変更:
   `schtasks /Change /TN SES_MatchingV3 /RI 120` (2時間毎)
   
   ※ /RIは分単位: 60=1時間, 120=2時間

3. 変更後に両タスクのスケジュールを `schtasks /Query /TN <name> /FO LIST` で確認してprint
