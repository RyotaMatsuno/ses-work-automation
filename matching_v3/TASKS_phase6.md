# TASKS — Phase 6: フィルタ設計刷新

## Phase 6A: alias正規化強化（1日目）
- [x] skill_aliases.jsonに高頻度alias追加（バージョン付き言語名、docker compose等）
- [x] 誤統合禁止リストのバリデーション追加（Java≠JavaScript等のテスト）
- [x] 正規化ログ出力（raw_skill / normalized_skill / rule_hit）
- [x] before/after ユニークスキル数比較レポート出力
- [x] pytest全PASS確認

## Phase 6B: 駅加点式 + フィルタ3層化（1-2日目）
- [x] config.py: HARD_FILTERS["remote_location"] = False に変更
- [x] config.py: SCORE_WEIGHTS 定数追加（skill:0.5, location:0.15, experience:0.15, availability:0.2）
- [x] station_master.json 新規作成（主要路線の駅→路線マッピング、初期版）
- [x] matcher.py: calc_location_score() 実装
- [x] matcher.py: calc_experience_score() 実装
- [x] matcher.py: calc_availability_score() 実装
- [x] matcher.py: フィルタ3層化（Hard → Soft Scoring → Rerank）
- [x] matcher.py: 候補ごとにscore_breakdown出力
- [x] matcher.py: Hard除外理由ログ出力
- [x] config.py: HARD_FILTERS を3層用に再定義

## Phase 6C: テスト + 検証（2日目）
- [x] tests/test_filter_3layer.py 新規作成
- [x] tests/test_location_score.py 新規作成
- [x] tests/test_experience_score.py 新規作成
- [x] tests/test_availability_score.py 新規作成
- [x] pytest全PASS確認（既存272件 + 新規テスト）
- [x] py_compile全ファイル確認
- [x] before/after 0件率比較レポート出力（research_results/に保存）
