# GPT Wall-Hit: Matching Root Cause - line_query.py独立実装問題
Date: 2026-06-19
Model: gpt-5.4

## 核心発見
「PH 京成小岩」はwebhook_server.py/run_reverse_matchingではなく
line_query/line_query.pyの独立マッチングで処理される。
2つの完全に別個のマッチングエンジンが存在し、ポリシーが乖離。

## line_query.pyの致命的フィルタ
1. L340: required_skills空 → 除外 (案件の58%が消える)
2. L347: gross > 15 → 除外 (PH 37万で70万案件=gross33→除外)
3. #skill_skip未対応 (webhook版は対応済み)

## GPT推奨
- P0: line_query.pyの3フィルタを緩和（最速の修正）
- P1: matching_core.pyに統合（webhook + line_query 共通化）
- #skill_skipは全フローで一貫適用すべき
- required_skills空は「不明」扱い、除外しない
- gross > 15はhard filterからscore調整に降格

## Task P更新指示
webhook_server.pyだけでなくline_query.pyも修正対象に追加。
理想はmatching_core.py共通化だが、まずline_query.pyの即効修正を優先。
