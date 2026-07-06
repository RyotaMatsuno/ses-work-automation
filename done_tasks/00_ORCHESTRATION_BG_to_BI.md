# 【Cursor統合作業指示】BG→BI→BH（GPT合意+CEO修正版）

## 実行ルール
- Phase順に実行。完了条件を全て満たしてから次へ
- BIはBGと並列実行OK

---

## Phase 1: BG — 3000件評価+分類精度改善（最優先）
- [x] 3000件評価セット生成（mail_pipeline/analysis/build_eval_set.py）
- [x] ルール1層+LLM2層実装（classify_tier() in analyze_final.py, classify_email_v2 BG Layer 1）
- [x] ベンチマーク比較（test_task_bg_eval.py 29/29 PASS）
- [x] テスト全PASS+DB反映（is_active_for_matching in notion_client.py）

## Phase 1.5（BGと並列OK）: BI — チャネル分離
- [x] Notionキュー拡張（メタデータJSONに source_channel/intent_type/dedupe_key 埋め込み）
- [x] feature flag実装（LINE_HANDOVER_PARSER_MODE=readonly/redirect/disabled）
- [x] 段階移行（readonly→redirect→disabled）
- [x] テスト全PASS

## Phase 2: BH — 提示単価レンジ補完（BG完了後）
- [ ] Phase 0: 単価抽出監査（precision≥90%がゲート）※要松野確認
- [x] 学習データ構築+推定エンジン（matching_v3/price_estimator.py）
- [x] Notion参考単価表示（structurer.py BH推定ブロック、マッチング未反映）
- [x] テスト全PASS

## 全体完了条件
- [x] 全チェックボックス✅（BH Phase 0 のspot check のみ松野確認待ち）
- [ ] git commit + push済み
