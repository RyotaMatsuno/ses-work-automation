# Task AD 完了: daily_stats カウンタ修正（P0）

完了日時: 2026-06-23 17:25

## 問題
- `daily_stats` の `match_count` / `review_count` が常に 0
- `processed_cases` には `business_status='matched'` と REVIEW verdict が存在

## 修正内容

### processed_db.py
- `update_status` からインクリメント方式のカウンタ更新を削除
- **`recompute_daily_stats(stat_date)`** — `processed_cases` から再集計して冪等 UPSERT
  - `match_count` = 当日 `business_status='matched'` 件数
  - `review_count` = 当日 `match_results_json` に REVIEW verdict を含む件数
  - `ng_count` = 当日 `business_status='ng'` 件数
  - `api_calls` / `total_cost_usd` も同日の `processed_cases` から再集計
- **`backfill_daily_stats()`** — 全期間バックフィル

### matching_v3.py
- 日次バッチ終了時に `db.recompute_daily_stats()` を呼び出し
- CLI: `--recompute-stats`（全期間バックフィル）、`--stat-date YYYY-MM-DD`（指定日のみ）

## 検証結果（本番 DB）

| stat_date | Before | After |
|---|---|---|
| 2026-06-23 | match=0, review=0 | **match=98, review=84** |

```bash
python matching_v3/matching_v3.py --recompute-stats --stat-date 2026-06-23
python matching_v3/matching_v3.py --recompute-stats  # 全期間バックフィル
```

## テスト
- `matching_v3/tests/test_processed_db.py` — **7/7 PASS**（再集計・冪等性・バックフィル追加）
