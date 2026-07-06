# 【Cursor作業指示】精度向上 Round 2 統合タスク

対象ディレクトリ: ses_work/
参照ファイル: CLAUDE.md / research_results/GPT_WALLHIT_PRECISION_R2_20260625_012608.md
完了条件: 全Phaseのテスト全PASS + dry-runレポート出力
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 実行ルール
- Phase 1->2->3->4->5->6の順に実行
- 各Phaseの完了条件を全て満たしてから次へ
- テスト落ちたらそのPhaseで止めて修正

---

## Phase 1: validate_skill() v2 強化

修正ファイル: `mail_pipeline/skill_extractor.py`

### 1A. 全角半角正規化（既存validate_skillの先頭に追加）
```python
import unicodedata
def normalize_skill_text(value: str) -> str:
    value = unicodedata.normalize('NFKC', value).strip()
    # 前後の記号除去
    value = re.sub(r'^[\s\-・:：\[\]【】]+|[\s\-・:：\[\]【】]+$', '', value)
    return value
```

### 1B. 追加ブラックリスト（SKILL_BLACKLISTに追記）
```python
# 記号のみ
r'^[】△▲○◎×>\)\(]+$',
# ラベル語
r'^(スキル|必須|尚可|歓迎|条件|経験)[:：]?$',
# 勤務形態
r'^(フルリモート|リモート|常駐|併用|出社|週\d)$',
# 月名・時期
r'^\d{1,2}月[〜~]?$',
r'^(即日|即参画|即稼働)$',
# 文末表現（文章混入）
r'(ください|です|ます|となります|ている|ですが|いたします|ございます|お願い)',
# ビジネス用語suffix
r'(案件|要員|募集|面談|単価|人材|配信|展開)$',
```

### 1C. suffix除去して再判定
```python
def strip_business_suffix(value: str) -> str:
    # "react案件" -> "react", "java要員" -> "java"
    return re.sub(r'(案件|要員|募集|人材)$', '', value).strip()
```
validate_skillでFalseになった場合、suffix除去後に再判定。成功したら除去後の値を返す。
filter_skillsの戻り値を変更: rejected + cleaned（suffix除去で救済された値リスト）

### 1D. 英語トークンルール
```python
# 純ASCII 3文字以下: エイリアス辞書に存在しなければreject
# "se","pm","pl","ml" -> 辞書にあればOK、なければreject
# 純ASCII 2文字未満: 常にreject
```

### テスト追加: `mail_pipeline/tests/test_skill_validator.py`
既存テストに追加:
```
追加VALID: "SE", "PM", "PL", "PMO", "QA", "iOS", "AI", "ML"
追加INVALID: "】", "△", ">", "6月", "7月", "フルリモート", "スキル", "スキル:",
             "ではありますが少し不足の場合はコメントと共にご提案ください",
             "条件の各項目について", "react案件", "java要員"
SUFFIX_CLEAN: ("react案件", "React"), ("java要員", "Java")
```

完了条件:
- [x] 全テストPASS
- [x] suffix除去ロジックが動作

---

## Phase 2: スキル辞書拡張 + 自動分類

### 2A. Tier 1 即時追加（skill_aliases.jsonに追加）

canonical_skillsに追加:
```
AI, SE, PM, PL, PMO, iOS, QA, ML, BigQuery, SwiftUI, AUTOSAR, Dataspider, Aurora
```

aliasesに追加:
```json
"ai": "AI",
"se": "SE", "system engineer": "SE",
"pm": "PM", "project manager": "PM",
"pl": "PL", "project leader": "PL",
"pmo": "PMO",
"ios": "iOS", "iphone": "iOS",
"qa": "QA", "quality assurance": "QA",
"bigquery": "BigQuery", "big query": "BigQuery", "bq": "BigQuery",
"s3": "AWS S3", "amazon s3": "AWS S3",
"fargate": "AWS Fargate",
"aurora": "AWS Aurora", "amazon aurora": "AWS Aurora",
"swiftui": "SwiftUI",
"autosar": "AUTOSAR",
"dataspider": "Dataspider",
"要件定義": "要件定義",
"基本設計": "基本設計",
"詳細設計": "詳細設計",
"テスト設計": "テスト設計",
"運用設計": "運用設計",
"ディレクション": "ディレクション",
"コミュニケーション": "コミュニケーション"
```

### 2B. 自動分類スクリプト: `matching_v3/auto_classify_skills.py`

1. Notion案件DBから全ユニークスキル値を収集
2. ルールベース分類:
   - validate_skill_v2でFalse -> GARBAGE
   - skill_aliases辞書にヒット -> CANONICAL
   - suffix除去でヒット -> CANONICAL (cleaned form)
3. 残りをGPT-4.1-nanoに一括送信（CostGuard経由、バッチ100件ずつ）:
   - 入力: スキル名 + 使用回数
   - 出力: class(tech_skill/role/process/garbage/unknown), canonical_form, confidence
4. 結果を3ファイルに出力:
   - `research_results/skill_classified_YYYYMMDD.json`（全結果）
   - `research_results/skill_add_candidates_YYYYMMDD.json`（辞書追加候補）
   - `research_results/skill_review_queue_YYYYMMDD.json`（人間レビュー必要分）
5. 辞書追加はdry-run（ファイル生成のみ、skill_aliases.json変更なし）

完了条件:
- [x] Tier 1スキルが辞書に追加済み
- [x] 分類スクリプトdry-run正常
- [x] 分類レポートが出力される（skill_classified_20260625.json 等）

---

## Phase 3: section-aware 必須/尚可 抽出

修正ファイル: `mail_pipeline/skill_extractor.py`

### ヘッダー検出パターン
```python
REQUIRED_HEADERS = [
    r'【必須】', r'■必須', r'必須スキル', r'必須条件', r'MUST',
    r'必要な経験', r'必須要件', r'求めるスキル',
]
OPTIONAL_HEADERS = [
    r'【尚可】', r'■尚可', r'■歓迎', r'尚可スキル', r'歓迎スキル',
    r'あると尚可', r'歓迎条件', r'あれば尚良', r'WANT', r'Nice to have',
]
SECTION_BREAK = [
    r'^【', r'^■', r'^━', r'^-{3,}', r'^\*{3,}',
    r'単価', r'勤務地', r'期間', r'面談', r'備考',
]
```

### 抽出ロジック
1. メール本文を行単位で分割
2. 各行をヘッダー検出でスキャン
3. current_section = None / "required" / "optional"
4. セクション内の行からスキル値を抽出
5. セクション未検出の場合: 従来通り全文から抽出し全て必須に格納
6. 抽出後に validate_skill + filter_skills を適用

### 戻り値変更
```python
# Before: return list[str]
# After: return {"required": list[str], "optional": list[str]}
```
呼び出し元（structurerまたはNotion書き込み）も修正。

### テスト: `mail_pipeline/tests/test_section_extraction.py`
```
テストケース:
1. 必須/尚可両方あるメール -> required/optional両方に値
2. 必須のみのメール -> requiredに値、optionalは空
3. セクションヘッダーなしのメール -> 全てrequiredに格納
4. 複数の必須ヘッダーバリエーション（【必須】,■必須,必須スキル）
5. 尚可が歓迎やWANTの場合
```

完了条件:
- [x] テスト全PASS
- [x] 必須/尚可が分離して返される
- [x] ヘッダーなしメールは従来通り動作

---

## Phase 4: 単価異常値一括修正 + ERRORリトライ実行

### 4A. 単価修正スクリプト: `matching_v3/fix_price_anomalies.py`

1. Notion案件DBから単価>200のレコードを全取得
2. 各レコードの案件情報原文を読み、年収キーワード検出
3. 年収キーワードあり -> 月額換算(÷12)
4. なし -> null化
5. dry-run -> `research_results/price_fix_dryrun_YYYYMMDD.md`
6. --execute -> Notion更新

### 4B. ERRORリトライ実行

`matching_v3/retry_errors.py --execute --batch 100`

Phase 1-3がデプロイ済みの前提で実行。
CostGuard $2超で中断。

完了条件:
- [x] 単価修正dry-runレポート出力（price_fix_dryrun_20260625.md）
- [ ] リトライ100件の結果レポート出力（--execute --batch 100、松野GO後）

---

## Phase 5: Notionクリーンアップ実行 + バックフィル実行

### 5A. cleanup_skills.py --execute
Phase 1のvalidate_skill v2でgarbage判定される全値をNotionから除去

### 5B. backfill_skills.py --execute
スキル空133件に対してPhase 3のsection-awareで再抽出→Notion書き込み

完了条件:
- [ ] cleanup実行ログ出力（--execute、松野GO後）
- [ ] backfill実行ログ出力（--execute、松野GO後）

---

## Phase 6: カバレッジ再計測

新規: `matching_v3/coverage_report.py`

最終計測:
- 辞書カバレッジ (target >50%)
- 必要スキル未設定率 (target <15%)
- 尚可スキル未設定率 (target <50%)
- 単価未設定率 (target <20%)
- 高品質率 (target >75%)
- マッチ数分布 (target avg <20)
- 単価異常値 (target 0)

結果: `research_results/precision_report_YYYYMMDD.md`

完了条件:
- [x] レポート出力（precision_report_20260625.md）
