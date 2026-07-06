# マッチング商用化 Phase 2: マッチング品質の実測と改善
Version: 1.0
Date: 2026-06-26
Status: GPT-5.4壁打ち2回完了、Phase 2A0 Cursor投入済み

---

## Phase 2 全体構成（GPT-5.4合意済み）

### Phase 2A0: Retrieval Collapse Fix（P0 — 最優先）
**状態: Cursorタスク投入済み**

問題: filter_engineers_by_required_skillsのAND交差ロジックにより
avg_matches = 0.2/案件（171名→0名が常態化）

修正: AND交差 → 閾値ベース（50%以上のスキル一致で候補生成）
- min_match = max(1, ceil(0.5 * len(resolved)))
- top-100キャップ
- Counter方式で高速化

期待効果: avg_matches 0.2 → 3.0以上

---

### Phase 2A1: ステータス管理 + Active Pool定義
**状態: 設計待ち（2A0完了後）**

目的: エンジニア208名の稼働状態を管理し、マッチング対象を絞り込む

設計方針:
- ステータスenum: 稼働可能 / 稼働中 / 待機中 / 非アクティブ
- 初期投入: 備考（LINEメモ）からのテキスト分析
- Active Pool = ステータスが「稼働可能」のエンジニアのみマッチング対象

---

### Phase 2A2: スキル正規化パイプライン
**状態: 設計待ち（2A0完了後）**

目的: エンジニアDBの正規化スキル（現在0%）を投入

設計方針:
- skill_aliases.jsonの既存辞書を活用
- Phase 1のengineer_extractorで抽出済みスキルのappend merge
- Top 100-200スキル/エイリアスで大部分をカバー

---

### Phase 2B: 評価インフラ構築
**状態: 設計中（2A0完了後に本格着手）**

目的: マッチング品質を客観的に計測する基盤

構成:
1. **50件パイロットベンチマーク**
   - stratified sampling（common/rare skills, exact/fuzzy, seniority, domain）
   - pooled annotation方式（top-10 × 3ソース + ランダム10 → 案件あたり20-35名アノテーション）
   - 3段階ラベル: Strong match / Interview-worthy / Not a match

2. **自動スコアリングパイプライン**
   - メトリクススイート:
     - zero-result rate
     - >=10候補率（Coverage）
     - Recall@10
     - strong-match@10
     - active-pool調整Recall@10
     - MRR or nDCG@10
   - per-case breakdown report
   - 時系列追跡

3. **失敗分類学**
   - skill synonym miss
   - over-strict AND logic
   - missing status
   - missing engineer data
   - missing case data
   - rank issue within retrieved set
   - true no-supply case

4. **ベースライン比較**
   - ランダム（Active Pool）
   - popularity-based
   - skill-overlap-only
   → システムがこれらを明確に上回ることを確認

---

### Phase 2C: ベンチマーク初回実行 + 改善
**状態: 2A0-2B完了後**

- 2A0修正後のbaseline計測
- 失敗taxonomy分析
- 改善実験（スキル正規化効果、ステータスフィルタ効果 etc.）
- 商用基準: Recall@10 >= 85%, Precision@10 >= 40%

---

## 現在のエンジニアDB状態（Phase 1完了後）

| フィールド | 投入率 | 備考 |
|---|---|---|
| 名前 | 100% (208/208) | |
| 単価（万円） | 91.3% (190/208) | Phase 1で+17件 |
| スキル | 90.9% (189/208) | Phase 1で+16件、avg 4.4/人 |
| 最寄り駅 | 28.8% (60/208) | Phase 1で+56件 |
| ステータス | 0% (0/208) | **要対応** |
| 経験年数 | 57.7% (120/208) | |
| 稼働可能日 | 27.4% (57/208) | |
| 居住地 | 0% (0/208) | |
| 正規化スキル | 0% (0/208) | **要対応** |
| 備考 | 100% (208/208) | |

## Goodhart's Lawガードレール（GPT-5.4合意）
1. strict "strong match" と broader "interview-worthy" の2指標を常に併記
2. stratifiedベンチマーク（ケースミックス固定）
3. precision/強match率をrecallと常に併記
4. Phase 3でheld-out set維持
5. Active Pool縮小時はpool sizeも追跡
6. profile completeness biasを認識

## 参照ドキュメント
- research_results/GPT_WALLHIT_phase2_spec.md（Round 1）
- research_results/GPT_WALLHIT_phase2_retrieval_fix.md（Round 2）
- research_results/GPT_WALLHIT_commercial_requirements.md（商用要件定義）
- matching_v3/SPEC_phase2a0.md（2A0 SPEC）


---

## 進捗更新 (2026-06-26 20:24)

### Phase 2A0: Retrieval Collapse Fix ✅ 完了
- avg_matches: 4.00 → **12.20** (目標3.0 ✅)
- AND交差 → 50%閾値 + top-100キャップ
- テスト: 7件PASS + 5件PASS
- 残課題: スキル12-13件の案件は依然0候補（OOV問題 → 2A2で改善予定）

### Phase 2A1: ステータス管理 + Active Pool — Cursor投入済み
- GPT-5.4合意: 除外ロジックのみ、未設定は空欄維持
- Cursorタスク: pending_tasks/20260626_202429_phase2a1_status_management.md

### Phase 2A2: スキル正規化 — Cursor投入済み
- GPT-5.4合意: alias/synonymのみ、rawフォールバック維持
- Cursorタスク: pending_tasks/20260626_202429_phase2a2_skill_normalization.md

### Phase 2B: 評価インフラ — 設計中（2A1+2A2完了後）
### Phase 2C: 初回計測 — 未着手
