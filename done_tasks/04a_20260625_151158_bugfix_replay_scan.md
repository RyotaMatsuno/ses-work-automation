【Cursor作業指示】
対象ディレクトリ: ses_work/
作業内容: Pilot発見バグ3件修正 + 安全スキャン + 全20件リプレイ検証
参照ファイル: CLAUDE.md / extractors/ / scripts/backfill_engine.py / golden_test/
完了条件: 3バグ修正 + 全20件リプレイPASS + 安全スキャンPASS + 回帰テストPASS

## 背景
Pilot 20件で3バグ+1軽微を発見。GPT-5.4レビュー済み。バッチbackfill前に修正・検証する。

---

## 修正1: rate単位変換バグ（最優先）

### 症状
「単価：55万」がNotionに550,000で格納された。

### 根本原因
extractor→backfill_engineのwrite pathで万→円変換が混入。

### 修正方針
extractors/rate_extractor.pyの出力は常に万単位の整数。write pathに変換ロジックを入れない。

1. rate_extractor.py: rate_min_man / rate_max_manは万単位の数値（55, 70, 120等）
2. scripts/backfill_engine.py: Notion書き込み時に変換しない。extractorの出力をそのままnumberフィールドに書く
3. write前バリデーション追加:
   - rate > 200 → ValueError（単位変換バグの可能性）
   - rate < 0 → ValueError
   - rate_min > rate_max → swap
4. 全コードパスで `* 10000` `* 10_000` 等の万→円変換を検索して削除

---

## 修正2: rate_extractorパターン拡張

### 症状
- 「70万（スキル見合い）」→ skill_dependent_no_number（数値を拾えていない）
- 「50万円前後」→ unknown（パターン未対応）

### 修正: regex Pass 1 のパターンを以下に更新（優先度順）

1. レンジ（最優先）: `(\d{2,3})\s*万円?\s*[〜～\-~]\s*(\d{2,3})\s*万` → fixed_range (conf=0.90)
2. スキル見合い+数値（前方）: `スキル見合.*?(?:MAX|max|Max|上限|〜|~|～|まで)?\s*(\d{2,3})\s*万` → skill_dependent_with_cap (0.90)
3. スキル見合い+数値（後方）: `(\d{2,3})\s*万円?.*?(?:スキル見合|経験見合|応相談)` → skill_dependent_with_cap (0.85)
4. MAX/上限: `(?:MAX|max|Max|上限)\s*[:：]?\s*(\d{2,3})\s*万` → fixed_upper_only (0.85)
5. 〜N万: `[〜～~]\s*(\d{2,3})\s*万` → fixed_upper_only (0.80)
6. N万まで: `(\d{2,3})\s*万円?\s*(?:まで|以下|以内)` → fixed_upper_only (0.80)
7. 概算: `(\d{2,3})\s*万円?\s*(?:前後|程度|目安|想定)` → fixed_upper_only (0.70)
8. 文脈内数値: `(?:単価|予算|金額|報酬)\s*[:：]\s*(\d{2,3})\s*万` → fixed_upper_only (0.75)
9. スキル見合い（数値なし）: `スキル見合|経験見合|ご経験見合|スキル次第` → skill_dependent_no_number (1.0)
10. 応相談: `応相談` → skill_dependent_no_number (0.80)

### 全角数字対応
パターンマッチ前にテキストを正規化（全角数字→半角、全角スペース→半角）

### マッチ窓の制限
各パターンは100文字以内の窓でマッチさせる（.*?の暴走防止）

---

## 修正3: remote_extractor「初日出社」対応

### SES業界セマンティクス（GPT-5.4確認済み）
「初日出社」= フルリモート案件で初日のみ出社（PC受取/顔合わせ）。hybridではない。

### 修正方針
full_remoteのまま維持 + initial_onsite_required=Trueフラグ追加

RemoteResultに `initial_onsite_required: bool` フィールドを追加。

### 一時出社パターン（full_remote維持、initial_onsite=True）
- 初日出社 / 初月出社 / 立ち上がり出社 / 参画初日出社
- 初回出社 / 初日のみ出社 / 入場初日出社
- セットアップ時出社 / PC受取.*出社 / 貸与物受取.*出社

### 定期出社パターン（hybrid判定に上書き）
- 週N出社 / 月N回出社 / 必要時出社 / 月1出社

### 処理順序
1. 一次分類（既存ロジック）
2. 一時出社チェック → initial_onsite_required設定（remote_type変更なし）
3. 定期出社チェック → remote_type=hybridに上書き

---

## 追加作業: 安全スキャン

### scripts/safety_scan.py
募集中の全案件で以下をチェック:
- rate > 200（単位変換バグ）
- rate > 1000（重大バグ）
- rate == 0（残存する旧データ）
- skill_dependent_no_number だが原文にN万パターンあり
- full_remote だが原文に定期出社パターンあり
出力: anomaly_report.csv

---

## 検証: 全20件リプレイ

### 手順
1. pilot 19件（v2タグ付き）の現在値をスナップショット
2. 修正版extractorで全19件を再抽出
3. before/after diff出力
4. 15件の正常ケースに変化がないこと確認（回帰テスト）
5. 3件のバグケースが修正されたこと確認
6. 1件のminorケースが改善されたこと確認

### 回帰テスト追加（golden_test/regression_test.pyに4テスト追加）
- 「70万（スキル見合い）」→ skill_dependent_with_cap, rate_max=70
- 「単価：55万」→ rate_max=55（550000ではない）
- 「フルリモート...初日出社有」→ full_remote + initial_onsite=True
- 「50万円前後」→ fixed_upper_only, rate_max=50

---

## 禁止事項
- 既存の必要スキル/尚可スキル抽出ロジック変更
- 15件の正常ケースの出力を変えること
- dry-runなしでNotionへの書き込み
- rate値に10000を掛ける変換

## 完了条件チェックリスト
- [x] rate_extractor.py パターン拡張完了
- [x] rate write pathの単位変換バグ修正（validate_rate_man + backfill/shadow）
- [x] remote_extractor.py initial_onsite_required追加
- [x] scripts/safety_scan.py 実行 → research_results/anomaly_report.csv
- [x] 全19件リプレイ diff確認（pilot_replay_diff_20260625.md）
- [x] 15件正常ケースに変化なし（回帰PASS）
- [x] 3件バグケース修正確認
- [x] golden_test/regression_test.py に4テスト追加 → PASS
