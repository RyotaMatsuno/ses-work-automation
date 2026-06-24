# 【Cursor作業指示】Task BG: 3000件実データ分析→分類精度改善（人員混入排除）

対象: ses_work/mail_pipeline/ + ses_work/matching_v3/
作業内容: raw_inbox.dbの実データ3000件を分析し、人員/案件の振り分け精度を向上させる
参照ファイル: CLAUDE.md / mail_pipeline/mail_pipeline.py / mail_pipeline/raw_inbox.db
完了条件: 人員混入率10%→1%以下
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## Phase 1: 3000件分析

### 1-1. 分析スクリプト作成（mail_pipeline/analysis/classify_audit_3000.py 新規）
- raw_inbox.dbから直近3000件のsubject + body_text + classify_resultを抽出
- project判定メールの中から人員混入を検出
- engineer/skip判定メールの中から案件取りこぼしを検出

### 1-2. 人員混入検出パターン
project判定されたが実は人材:
- 「若手/ベテラン/中堅/シニア + 人材/エンジニア/技術者」
- 「人材/要員/技術者 + 紹介/ご紹介/ご案内/配信」
- 「NN歳/男性/女性」プロフィール形式
- 「弊社プロパー/フリーランス + 紹介」
- 「稼働可能/即日参画 + 人材」
- 「おすすめ人材/注力要員」
- 「スキルシート送付/経歴書添付」
- 「人材配信/要員配信」

### 1-3. 案件取りこぼし検出パターン
engineer/skipだが実は案件:
- 「案件 + 技術キーワード(Java/PHP/Python等)」
- 「NN万 + 案件/募集/開発」
- 「案件概要/業務内容/担当工程/募集人数/スキル要件」

### 1-4. レポート出力（mail_pipeline/analysis/audit_result_3000.json）

## Phase 2: 分類ルール修正（analyze_final.py）
- Phase 1の結果に基づきSTRONG_ENGINEER_PATTERNSに不足パターン追加
- 「人材」キーワードの重み調整
- 件名に「人材」「要員」+人名パターン → engineer確定ルール
- 既存テスト30/30が壊れないこと

## Phase 3: テスト + 案件DBクリーニング
- test_task_bg_engineer_leak.py 新規（検出した混入パターン10件をテストケース化）
- 案件DBの既存ページを再スキャン、人員混入をmatching_status="engineer_misclass"に更新

## 完了条件
- [ ] 3000件分析レポート生成
- [ ] 分類ルール修正
- [ ] 新規テスト+既存テスト全PASS
- [ ] 案件DBクリーニング実行
