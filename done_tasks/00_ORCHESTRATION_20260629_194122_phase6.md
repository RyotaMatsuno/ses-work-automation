# 00_ORCHESTRATION — Phase 6: フィルタ設計刷新
生成: 2026-06-29 by ジョブズ
GPT-5.4壁打ち5回GO済み

---

## 実行順序（直列）

### Step 1: Phase 6A — alias正規化強化
- 3点セット: matching_v3/CLAUDE_phase6.md, SPEC_phase6.md, TASKS_phase6.md
- skill_aliases.jsonに高頻度alias追加
- 誤統合禁止テスト追加
- 完了条件: pytest全PASS + before/afterレポート

### Step 2: Phase 6B — 駅加点式 + フィルタ3層化
- config.py HARD_FILTERS変更 + SCORE_WEIGHTS追加
- station_master.json作成
- matcher.py: 3層フィルタ実装（Hard→Soft→Rerank）
- 完了条件: pytest全PASS + score_breakdown出力確認

### Step 3: Phase 6C — テスト + 検証
- 新規テスト4ファイル作成
- 全テストPASS
- before/after 0件率比較レポート

---

## 共通ルール
- 既存272テストを壊さない
- Java≠JavaScript等の誤統合は絶対禁止
- py_compile必須
- CostGuardなしでLLM呼び出さない
