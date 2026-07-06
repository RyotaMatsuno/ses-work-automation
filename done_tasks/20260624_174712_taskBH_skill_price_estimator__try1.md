# 【Cursor作業指示】Task BH: 提示単価レンジ補完（GPT-5.4 3ラウンド合意版）

対象: ses_work/matching_v3/
参照: CLAUDE.md / matching_v3/structurer.py / mail_pipeline/raw_inbox.db
完了条件: 「スキル見合い」案件にNotion上で参考単価レンジが表示される
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 目的定義（GPT合意）
「メール本文に単価明示がない案件に対して、過去の明示単価案件の分布から参考単価レンジを補完表示する機能。成約単価予測ではなく、社内優先順位付けの補助情報であり、自動意思決定には使用しない。」

## Phase 0: 単価抽出監査（最優先）

### 0-1. 200件サンプル手動確認
- raw_inbox.dbのproject判定メールからランダム200件
- 各メールのbudget_min_raw/max_rawの抽出精度を確認
- 指標: 単価抽出precision（正しく数値化されている率）

### 0-2. 単位揺れの正規化ルール確定（GPT注意点）
実装前に以下を固定:
- 月額/時給/年収 → 全て月額万円に統一
- 税込/税別 → 税別に統一（SES業界慣行）
- 上限のみ/下限のみ → そのまま保持（片側null）
- 「前後」→ ±5%レンジ
- 「スキル見合い」「応相談」→ budget_source="unknown"

### 0-3. ゲート判定
- 単価抽出precision ≥ 90% → Phase 1へ進む
- < 90% → structurer.pyの単価抽出ロジックを先に修正

## Phase 1: 学習データ構築（matching_v3/price_estimator.py 新規）

### 1-1. 明示単価あり案件を収集
- budget_source="explicit"の案件のみ
- 抽出: budget_min, budget_max, skills[], role, phase(工程), location
- 外れ値除去（IQR法）

### 1-2. 階層バックオフ統計
- Level 1: ロール別（PG/SE/PMO/インフラ/テスト）
- Level 2: ロール×工程（製造/詳細設計/基本設計/要件定義）
- Level 3: ロール×工程×主要スキル群（Java系/Python系/AWS系/SAP系）
- Level 4: 地域補正（東京/大阪/名古屋/リモート）
- n≥30: そのレベル採用
- 10≤n<29: 1レベル上にバックオフ + confidence_rank="low"
- n<10: budget_source="unknown"（推定しない）

### 1-3. 推定ルール生成（matching_v3/price_rules.json 自動生成）
fallback: 判断マニュアルv3の適正単価テーブル
- 上級SE(要件定義〜): 75〜80万
- SE(基本設計〜): 65〜70万
- 上級PG(詳細設計〜): 55〜60万
- PG(製造中心): 45〜50万

## Phase 2: 推定エンジン + DB反映

### 2-1. estimate_price() 実装
返却: estimated_min, estimated_max, confidence_rank(high/medium/low), method

### 2-2. structurer.pyへの統合
- budget_textが「スキル見合い」「応相談」等 → estimate_price()呼出
- 新フィールド: budget_estimated=true

### 2-3. Notion案件DB
- budget_min_raw / budget_max_raw: メールから直接抽出した値
- budget_min_estimated / budget_max_estimated: 推定値
- budget_source: explicit / estimated / unknown
- budget_confidence_rank: high / medium / low
- budget_estimation_version: v1_YYYYMMDD

### 2-4. 利用制限（MVP）
- Notionに「参考単価」として表示のみ
- マッチングスコアには反映しない（Phase 2で検討）

## Phase 3: 評価
- 時系列分割CV（直近20%テスト、残り学習）
- 指標: MAE、±5万的中率、±10万的中率
- 判断マニュアル適正単価テーブルとの乖離チェック

## 完了条件
- [ ] Phase 0: 単価抽出監査完了（precision≥90%がゲート）
- [ ] Phase 1: 学習データ構築+price_rules.json生成
- [ ] Phase 2: 推定エンジン+structurer統合+Notion反映
- [ ] budget_source/confidence_rankが正しく設定される
- [ ] 推定値はマッチングに未反映（表示のみ）
- [ ] テスト全PASS


## RETRY 1 REASON
target_file not found: 
