# 【Cursor作業指示】Task BH: 「スキル見合い」単価推定エンジン

対象: ses_work/matching_v3/
作業内容: 案件データから「スキル見合い」の実際の単価目安を推定し自動入力する
参照ファイル: CLAUDE.md / matching_v3/structurer.py / mail_pipeline/raw_inbox.db
完了条件: 「スキル見合い」案件に推定単価が自動入力される
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 背景
- 案件メールの単価欄に「スキル見合い」「応相談」「スキルに応じて」等が多い
- 実際は業界相場・スキルセット・工程から目安単価が推測可能
- CEO指示:「案件数千件見れば判定できるはず。目安で単価入れれるようにして」

## Phase 1: 学習データ構築（matching_v3/price_estimator.py 新規）

### 1-1. 明示単価あり案件の収集
- raw_inbox.dbのproject判定メールから単価情報を抽出
- パターン: "XX万" "XX〜YY万" "〜XX万" "XX万〜"
- 各案件: budget_min, budget_max, skills[], role, phase(工程), location

### 1-2. スキル×工程×ロール別の単価分布算出
例:
- Java + 詳細設計〜 → 中央値62万, P25=58万, P75=68万
- Python + 基本設計〜 → 中央値68万, P25=63万, P75=75万
- PMO → 中央値75万, P25=65万, P75=85万

### 1-3. 推定ルール生成（matching_v3/price_rules.json 新規・自動生成）
条件→推定単価帯のマッピング + confidence + sample_count
fallback: 判断マニュアルv3の適正単価テーブル
- 上級SE(要件定義〜): 75〜80万
- SE(基本設計〜): 65〜70万
- 上級PG(詳細設計〜): 55〜60万
- PG(製造中心): 45〜50万

## Phase 2: 推定エンジン実装

### 2-1. estimate_price(skills, phase, role, location) → dict
返却: estimated_min, estimated_max, confidence, method("rule_based"/"fallback"/"unknown")

### 2-2. structurer.pyへの統合
- budget_textが「スキル見合い」「応相談」等の場合にestimate_price()を呼出
- budget_min/maxに推定値を入力
- 新フィールド: budget_estimated=true（推定値の明示）

### 2-3. Notion案件DBへの反映
- 推定単価をNotionに保存
- プロパティ追加: 推定単価(number)、単価推定フラグ(checkbox)

## Phase 3: 整合性チェック
- 推定値と判断マニュアルの適正単価テーブルの乖離を検出→警告ログ
- 学習データの更新は月次再実行可能な設計

## 完了条件
- [ ] 学習データ構築+統計分析
- [ ] 推定エンジン実装+structurer統合
- [ ] 「スキル見合い」案件に推定単価が入力される
- [ ] テスト全PASS
- [ ] budget_estimated=true フラグが必ず付与される
