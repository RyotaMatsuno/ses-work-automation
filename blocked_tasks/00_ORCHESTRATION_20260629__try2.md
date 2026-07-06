# 00_ORCHESTRATION — Cursor一括実行指示書
生成: 2026-06-29 12:50 by ジョブズ
GPT-5.4壁打ち反映: 2026-06-29 13:30

---

## 重要方針（GPT-5.4壁打ちによる修正）

1. **開発は並列OK、本番反映・評価は直列化**
2. **推定単価のみで自動NGしない。REVIEW扱い。**
3. **判定結果に judge_version / unit_price_source を記録**

---

## 実行順序

### Phase A-2（先行）: engineer_extractor — エンジニアDB品質改善
- **3点セット**: engineer_extractor/CLAUDE.md, SPEC.md, TASKS.md
- **内容**: E2(summary report確認)から再開 → E3(30件manual review) → E4(抽出器修正) → F1-F5(段階適用)
- **完了条件**: TASKS.md の全チェックボックス完了
- **ゲート条件（段階apply）**:
  - F1(10件): 手動レビュー一致率 >= 80%
  - F3(50件): unknown skill率 <= 15% + summary破綻率 <= 5%
  - F4(全件): F3ゲート通過 + before/afterスナップショット保存
- **注意**: apply対象を分離 → summaryのみ先行、skills後追い、単価関連は最後
- **ロールバック**: before/afterスナップショットをresearch_results/に保存

### Phase A-1（A-2反映後）: matching_v3 Phase 5 — Judge精度改善
- **3点セット**: matching_v3/CLAUDE_phase5.md, SPEC_phase5.md, TASKS_phase5.md
- **内容**:
  - judge()の粗利判定3値化（PASS/NG/REVIEW）— 推定単価でNG禁止
  - judge()の未知スキルを必須/尚可分離（尚可のみ未知はINFO）
  - judge()の並行スコア>=5.0 NG化 + 欠損時REVIEW
  - get_active_engineers()に提案対象フラグfilter追加（fail-open方式）
  - judge結果にunit_price_source/gross_profit_calc_status/judge_version記録
- **完了条件**: TASKS_phase5.md の全チェックボックス完了 + py_compile PASS
- **（A-2の反映完了が前提）**: A-2のDB品質変更が安定してからJudge仕様を変える

### Phase B（Phase A完了後）: matching_v3 Phase 3 — CostGuard Ledger統合
- **3点セット**: matching_v3/CLAUDE_phase3.md, SPEC_phase3.md, TASKS_phase3.md
- **内容**: structurer.py/cost_guard.py/outlook_to_notion.py/mail_attachment_importer にledger統合
- **前提**: Phase A-1の粗利算式とledger粗利算式の整合を確認してから着手
- **完了条件**: TASKS_phase3.md の全チェックボックス完了 + py_compile PASS

### Phase C（Phase B完了後）: cost_guard_v2 — 残タスク完了＋デプロイ
- **3点セット**: cost_guard_v2/CLAUDE.md, SPEC.md, TASKS.md
- **内容**: 統合テスト(7.x)→レビュー(9.x)→デプロイ(10.x)
- **完了条件**: TASKS.md の全チェックボックス完了
- **注意**: Phase 10（デプロイ）はClaude.aiチャットに貼り付けて松野確認を取ること

---

## 共通ルール
- 各Phaseの詳細仕様は各フォルダの3点セット（CLAUDE.md/SPEC.md/TASKS.md）を参照
- Phase間で依存がある場合は完了条件を満たしてから次に進む
- 実装中にエラーが出た場合はClaude.aiチャットに貼り付けて確認
- `py_compile` での構文確認は各Phase完了時に必ず実施
- テスト実行: `cd matching_v3 && python -m pytest tests/ -v`
- CostGuardなしでLLMを呼び出さない
- 判定結果に judge_version を記録（Phase A-1）


## RETRY 1 REASON
Claude Code TIMEOUT

## 進捗状況（2026-06-29 更新）

- Phase A-2 (engineer_extractor): ✅ 全完了
- Phase A-1 (matching_v3 Phase 5): ✅ 全完了
- Phase B (matching_v3 Phase 3): ✅ 全完了
- Phase C (cost_guard_v2):
  - 7.5 line_bridge.py 置換: ✅ 完了（cost_guard.allowed()/finalize() 統合）
  - 9.x ゲート②: ✅ GO確認済み（gate2_review_v2.10.1_final.md）
  - test 修正: db_error_blocked reason追加（15値）→ 165テスト PASS
  - Dockerfile 更新: cost_guard.py + common/ をコピーするよう変更
  - **10.x デプロイ: 松野確認待ち** → Phase 10 実行には松野のCloud Run承認が必要


## RETRY 2 REASON
target_file not found: (前回セッションのタイムアウト)

## try2 完了状況（2026-06-29 更新）

- matching_v3 テスト修正（try2): ✅ 完了
  - skill_aliases.json: soft_aliases "c"→"C", hard "llm"→"生成AI", parent_skills "PL/SQL":"SQL" 追加
  - matcher.py: parent-hint miss → NG でなく REVIEW（unknown_skills扱い）
  - auto_classify_skills.py: _classify_rule_based に suffix strip fallback 追加
  - tests: 粗利不足/大文字小文字修正
  - 272テスト全PASS確認
- **Phase 10（デプロイ）: 松野確認必要** → 以下の手順を松野にLINEまたはClaude.aiで確認を取ること

```
【Phase 10 デプロイ手順 - 松野確認待ち】
10.1 既存 cron / Task Scheduler から旧 cost_guard 系を停止
10.2 新 ledger / cost_guard を本番デプロイ（Cloud Run line-webhook 含む）
10.3 24時間モニタリング
10.4 SES Knowledge Wiki に「装置1〜3 v2.4 デプロイ完了」追記
10.5 旧 cost_state.json.bak_v2.4 を3ヶ月保持
```


## BLOCKED REASON
target_file not found: 
