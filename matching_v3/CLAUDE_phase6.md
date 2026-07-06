# CLAUDE.md — Phase 6: フィルタ設計刷新

## 目的
0マッチ率50%→15%以下。Recall@10 ≥ 85%達成のための前段フィルタ再設計。

## 絶対ルール
- 既存テスト272件を壊さない（pytest全PASS維持）
- CostGuardなしでLLM呼び出さない
- skill_aliases.jsonのalias追加時、Java≠JavaScript等の誤統合は絶対禁止
- matcher.pyの変更はPhase 5（Judge v5.1）と競合しないこと
- 変更前後のbefore/afterスナップショットをresearch_results/に保存

## フィルタ3層設計（新アーキテクチャ）
```
Hard（絶対条件のみ）→ Soft（加点減点）→ Rerank（総合スコア順）
```
- Hardで落とすのは「契約不可」「稼働完全不可」のみ
- 駅・経験年数・稼働日はSoft層に移動（ハードフィルタから外す）
- 各候補にscore_breakdownを付与

## コーディングルール
- py_compile必須
- テスト: cd matching_v3 && python -m pytest tests/ -v
- 新機能には必ずテスト追加
- config.pyの定数はハードコードせずconfig経由
