# 【Cursor作業指示】reclass枠starvationバグ修正 + デバッグログ追加

## 対象ディレクトリ
ses_work/mail_pipeline/

## 背景
fetch_unprocessed_from_db(limit=200) で fresh 80% / reclass(other) 20% 比率分割を実装済みだが、
パイプライン実行時のログで fresh:200 / reclass:0 が連続している。
DB直叩きシミュレーションでは fresh=160 / reclass=40 が正しく取れるため、
実行コンテキストでのみ発生する間殇バグと推定。

## 修正方針（GPT-5.4壁打ち2回で合意済み）

### 修正1: fetch_unprocessed_from_db の返り値をタプル化
ファイル: raw_inbox.py

現在: list[dict] を返す
変更後: tuple[list[dict], list[dict]] を返す (fresh_items, reclass_items)

具体的に:
1. 既存のdict変換ロジック(lines 237-259)を _row_to_dict(row) ヘルパー関数に抽出
2. fresh_rowsとreclass_rowsをそれぞれ別々にdict変換
3. 各itemに "_queue_type": "fresh" または "reclass" を追加
4. return fresh_items, reclass_items

### 修正2: _main_body の呼び出し側修正
ファイル: mail_pipeline.py

現在 (lines 1846-1848):
```python
work_items = fetch_unprocessed_from_db(limit=process_limit, db_path=RAW_INBOX_DB)
fresh_items = [em for em in work_items if em.get("classify_result") is None]
reclass_items = [em for em in work_items if em.get("classify_result") == "other"]
```

変更後:
```python
fresh_items, reclass_items = fetch_unprocessed_from_db(limit=process_limit, db_path=RAW_INBOX_DB)
work_items = fresh_items + reclass_items
```

### 修正3: デバッグログ追加（3箇所）

#### 3a. _save_all_emails_to_raw_inbox 前後 (mail_pipeline.py)
_save呼び出しの前後で、processed=0のother件数とnull件数をログ。
ヘルパー関数 _count_by_classify(value, db_path) を作成。
プレフィックス: [DEBUG]

```python
def _count_by_classify(classify_result_value, db_path=None):
    from mail_pipeline.raw_inbox import get_connection
    conn = get_connection(db_path or RAW_INBOX_DB)
    try:
        if classify_result_value is None:
            return conn.execute("SELECT COUNT(*) FROM raw_emails WHERE processed=0 AND classify_result IS NULL").fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM raw_emails WHERE processed=0 AND classify_result=?", (classify_result_value,)).fetchone()[0]
    finally:
        conn.close()
```

使い方:
```python
_pre_other = _count_by_classify("other")
_pre_null = _count_by_classify(None)
log(f"[DEBUG] pre-save: other={_pre_other} null={_pre_null}")
_save_all_emails_to_raw_inbox(emails)
_post_other = _count_by_classify("other")
_post_null = _count_by_classify(None)
log(f"[DEBUG] post-save: other={_post_other} null={_post_null} diff_other={_post_other-_pre_other} diff_null={_post_null-_pre_null}")
```

#### 3b. fetch_unprocessed_from_db 内部 (raw_inbox.py)
SQL取得直後にログ:
```python
import logging
_logger = logging.getLogger(__name__)
# fresh_rowsとreclass_rows取得直後に:
_logger.info("[DEBUG] fetch_db SQL: fresh_rows=%d reclass_rows=%d", len(fresh_rows), len(reclass_rows))
```

#### 3c. _main_body 受取直後 (mail_pipeline.py)
```python
fresh_items, reclass_items = fetch_unprocessed_from_db(...)
work_items = fresh_items + reclass_items
log(f"[DEBUG] received: fresh={len(fresh_items)} reclass={len(reclass_items)} total={len(work_items)}")
cr_dist = {}
for em in work_items:
    cr = em.get("classify_result")
    cr_dist[cr] = cr_dist.get(cr, 0) + 1
log(f"[DEBUG] classify_result dist: {cr_dist}")
```

### 修正4: fetch_unprocessed_from_dbの全呼び出し箇所確認
全文検索で fetch_unprocessed_from_db を呼んでいる箇所を全て見つけ、
返り値の型変更に対応する。
影響がある場合はタプル展開で受け取るように修正。

## 参照ファイル
- CLAUDE.md: ses_work/CLAUDE.md
- 壁打ち結果: ses_work/research_results/GPT_WALLHIT_RECLASS_STARVATION_20260619.md

## 完了条件
1. fetch_unprocessed_from_db が tuple[list[dict], list[dict]] を返す
2. _main_body がタプルで受け取り、classify_resultからの再判定をしない
3. 3箇所の[DEBUG]ログが追加されている
4. _row_to_dict ヘルパー関数が抽出されている
5. _queue_type フィールドが各itemに設定されている
6. 全呼び出し箇所が新しい返り値型に対応済み

## 注意事項
- CostGuardに影響しない変更のみ
- デバッグログは [DEBUG] プレフィックスで統一
- sys.stdout.reconfigure(encoding='utf-8', errors='replace') をスクリプト先頭に入れること
