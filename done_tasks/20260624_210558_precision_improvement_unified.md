# 【Cursor作業指示】精度向上統合タスク AA+AB

対象ディレクトリ: ses_work/
参照ファイル: CLAUDE.md
完了条件: 全Phaseのテスト全PASS + dry-runレポート出力
質問がある場合: Claude.aiチャットに貼り付けて確認

---

## 実行ルール
- Phase 1→2→3→4→5→6の順に実行。各Phase完了後に次へ進む
- 各Phaseの完了条件を全て満たしてから次へ
- テストが落ちたらそのPhaseで止めて修正

---

## Phase 1: skill_extractor バリデーション追加

修正ファイル: `mail_pipeline/skill_extractor.py`

既存の抽出関数の出力側にバリデーション層を追加する。
既存のextract系関数のreturn直前にfilter_skills()を挿入し、rejected分はloggerに記録。

```python
import re, logging
logger = logging.getLogger(__name__)

SKILL_BLACKLIST = [
    r'\d+[万円]',
    r'[~〜～]\d|[0-9][~〜～]',
    r'[☆★!！*＊]',
    r'【.*】',
    r'歳まで|歳以上',
    r'月[〜~]|[〜~]月',
    r'相談可|増員|弊社|注力|募集|配信|展開',
    r'即日|即稼働|即参画',
    r'常駐案件|案件情報|要員情報',
]

def validate_skill(value: str) -> bool:
    value = value.strip()
    if len(value) < 2 or len(value) > 30:
        return False
    for pat in SKILL_BLACKLIST:
        if re.search(pat, value):
            return False
    if re.fullmatch(r'[\d０-９.]+', value):
        return False
    if re.fullmatch(r'[A-Za-z0-9#.+/\- ]{2,30}', value):
        return True
    if re.fullmatch(r'[\u30A0-\u30FFー]{2,15}', value):
        return True
    if re.fullmatch(r'[\u4E00-\u9FFF\u30A0-\u30FF\u3040-\u309F]{2,12}', value):
        return True
    if re.fullmatch(r'.{2,15}(経験|設計|構築|開発|運用|保守|管理|テスト|移行)', value):
        return True
    if len(value) <= 20 and re.search(r'[A-Za-z]', value) and re.search(r'[\u3000-\u9FFF]', value):
        return True
    return False

def filter_skills(raw_skills: list) -> list:
    valid, rejected = [], []
    for s in raw_skills:
        (valid if validate_skill(s) else rejected).append(s)
    if rejected:
        logger.info(f"Rejected {len(rejected)} invalid skills: {rejected[:5]}")
    return valid
```

### テスト: `mail_pipeline/tests/test_skill_validator.py`

VALID例: "Java", "AWS", "Spring Boot", "C#", "Python", "Docker", "React", "インフラ", "ネットワーク", "要件定義", "基本設計", "Vue.js", "Oracle", "SQL Server", "Linux運用", "CI/CD"
INVALID例: "65~75万円", "110~150万円", "*弊社増員枠", "50万円", "7月〜", "8月相談可能☆常駐cobol案件☆55歳まで", "即日", "2名", "", "a", "弊社注力案件でして", "65〜95万", "80万~90万"

parametrizeで全パターン網羅。filter_skillsのテストも含める。

完了条件:
- [x] テスト全PASS (test_skill_validator.py 4件)
- [x] 既存extract関数がfilter_skills()経由で出力

---

## Phase 2: マッチ数爆発の根本原因修正

修正ファイル: `matching_v3/` 配下（matching_batch.py, matcher.py, matching_v3.py 等）

### 調査→修正（コードを読んで以下を確認し修正）

1. スキル空案件の処理: 必要スキル=空のとき全員マッチしている→空ならSKIPPED（マッチ不可）にする
2. スコア閾値: 閾値が0や極小値なら適正値（1点以上等）に修正
3. 20件上限ガード: match_results_json書き込み前にscore降順ソート→top 20トリム
4. 単価空案件: 単価なしでも全員マッチしていないか確認→スコアペナルティ追加

### テスト: `matching_v3/tests/test_match_quality.py`

- test_empty_skill_project_skipped: 必要スキル空→SKIPPED
- test_match_count_max_20: 結果が常に20件以下
- test_match_sorted_by_score_desc: スコア降順

完了条件:
- [x] テスト全PASS (test_match_quality.py 3件 + test_task_ab.py 8件)
- [x] スキル空案件が0マッチ(SKIPPED)になること
- [x] match_results_jsonが常に20件以下

---

## Phase 3: price_extractor バリデーション強化

修正ファイル: `mail_pipeline/price_extractor.py`

validate_price()を追加:
- value > 200: 年収キーワード(年収/年俸/賞与込)あり→÷12、なし→null
- value < 20: 日額キーワード(日額/日給//日)あり→×20、なし→null
- それ以外: そのまま通す

既存のextract関数のreturn直前に挿入。

### テスト: `mail_pipeline/tests/test_price_validator.py`

- 通常値(65)→そのまま
- 年収(600, "想定年収600万")→50.0
- 異常値(430000)→null
- 日額(3.5, "日額3.5万")→70.0
- 低値(1.5, キーワードなし)→null

完了条件:
- [x] テスト全PASS (test_price_validator.py 13件)

---

## Phase 4: Notionクリーンアップスクリプト（dry-run専用）

新規: `matching_v3/cleanup_skills.py`

実行: `python cleanup_skills.py`（dry-runのみ。--executeは松野確認後）

処理:
1. 案件DB(募集中)の全レコードから必要スキル取得
2. validate_skill() + skill_aliases辞書で判定
3. canonical/garbage/review の3カテゴリに分類
4. レポート出力: `research_results/skill_cleanup_dryrun_YYYYMMDD.md`
5. バックアップ: `research_results/skill_backup_YYYYMMDD.json`
6. Notion API 0.4秒間隔、50件バッチ

完了条件:
- [x] cleanup_skills.py 作成済み（dry-run実行は松野GO後）

---

## Phase 5: スキル空レコード バックフィル（dry-run専用）

新規: `matching_v3/backfill_skills.py`

実行: `python backfill_skills.py`（dry-runのみ）

処理:
1. 募集中 AND 必要スキル=空 AND 案件情報原文≠空 のレコード取得
2. Phase 1のバリデーション付きextractorで再抽出
3. レポート出力のみ

完了条件:
- [x] backfill_skills.py 作成済み（dry-run実行は松野GO後）

---

## Phase 6: ERRORリトライスクリプト（dry-run専用）

新規: `matching_v3/retry_errors.py`

実行: `python retry_errors.py`（dry-runのみ）

処理:
1. processed_casesのERROR AND retry_count < 3 を取得
2. 件数と日付分布をレポート
3. --execute --batch 50 で本番実行（松野確認後）
4. CostGuard: $2超で中断

注意: Phase 2のマッチ品質修正がデプロイ済みの前提

完了条件:
- [x] retry_errors.py 作成済み（dry-run実行は Phase 2 デプロイ後）
