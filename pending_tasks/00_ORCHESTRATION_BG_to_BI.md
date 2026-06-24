# 【Cursor統合作業指示】BG→BI→BH（GPT-5.4合意版）

## 実行ルール
- Phase順に実行。完了条件を全て満たしてから次へ
- BIはBGと並列実行OK

---

## Phase 1: BG — 200件評価+分類精度改善（最優先）
- [ ] 200件評価セット生成
- [ ] ルール1層+LLM2層実装
- [ ] ベンチマーク比較
- [ ] テスト全PASS+DB反映

## Phase 1.5（BGと並列OK）: BI — チャネル分離
- [ ] Notionキュー拡張
- [ ] feature flag実装
- [ ] 段階移行（readonly→redirect→disabled）
- [ ] テスト全PASS

## Phase 2: BH — 提示単価レンジ補完（BG完了後）
- [ ] Phase 0: 単価抽出監査（precision≥90%がゲート）
- [ ] 学習データ構築+推定エンジン
- [ ] Notion参考単価表示（マッチング未反映）
- [ ] テスト全PASS

## 全体完了条件
- [ ] 全チェックボックス✅
- [ ] git commit + push済み
