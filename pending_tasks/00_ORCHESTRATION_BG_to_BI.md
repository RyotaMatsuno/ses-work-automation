# 【Cursor統合作業指示】BG→BH→BI

## 実行ルール
- Phase順に実行。完了条件を全て満たしてから次へ
- BI（チャネル分離）はBGと並列実行OK

---

## Phase 1: BG — 3000件分析+分類精度改善
**詳細**: `pending_tasks/20260624_174712_taskBG_classify_3000_audit.md`
- [ ] 3000件分析レポート
- [ ] 分類ルール修正
- [ ] テスト全PASS
- [ ] 案件DBクリーニング

## Phase 2: BH — スキル見合い単価推定（BG完了後）
**詳細**: `pending_tasks/20260624_174712_taskBH_skill_price_estimator.md`
- [ ] 学習データ+統計分析
- [ ] 推定エンジン+structurer統合
- [ ] テスト全PASS

## Phase 1.5（並列OK）: BI — チャネル分離反映
**詳細**: `pending_tasks/20260624_174712_taskBI_channel_separation.md`
- [ ] Notionキューclaude_mobile追加
- [ ] 引き継ぎパーサーLINE廃止
- [ ] テスト全PASS

## 全体完了条件
- [ ] 全チェックボックス✅
- [ ] git commit + push済み
