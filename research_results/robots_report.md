# Phase 2 robots.txt 確認結果（2026-07-01）

## エンゲージ（en-gage.net）
- `/search2/` : **許可** (crawl_delay 10秒以上推奨)
- 実装: `crawl_phase2_engage.py` 実行中

## Green（green-japan.com）
- `/search` : **Disallow** → 直接検索クロールは**スキップ**
- 代替: `phase1_urls_dedup.csv` 内の Green 求人URLを `crawl_phase2_green.py` で詳細取得

## Google検索
- ヘッドレスアクセスは CAPTCHA (`/sorry`) でブロック
- 代替: エンゲージ直接一覧クロールを Phase 1 の主データソースに採用
- Bing検索は `--skip-search` なしで補助的に試行（結果は環境依存）

## 松野さんへの Phase 2 確認事項
- Green `/search` Disallowのため、Green直接クロールは Phase1経由URLのみ
- エンゲージ Phase2 全件（約1036件）詳細取得は **約3時間**（10秒/件）見込み
- バックグラウンド実行中: `crawl_phase2_engage.py`
