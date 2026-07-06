import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import os
from datetime import datetime

PENDING = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pending_tasks"
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

# ================================================================
# 00_ORCHESTRATION
# ================================================================
orch = f"""# 00_ORCHESTRATION — 精度改善R5（抽出品質+マッチング精度）
# 生成: {ts}
# 総タスク数: 8
# 松野チェックポイント: 3回（CP1:Task5後, CP2:Task6後, CP3:Task8後）

## Phase順序（厳守）

### Phase A（並列OK: Task 1,2,3）
- 01_baseline_golden_set.md — ベースライン凍結+60件ゴールデンセット
- 02_notion_schema.md — Notionスキーマ追加（rate_type/remote_type等）
- 03_extractors.md — 純粋関数extractor実装（rate/remote/location）

### Phase B（Phase A完了後）
- 04_merge_backfill_engine.md — マージポリシー+dry-run/rollback+shadow mode統合+20件pilot backfill

### Phase C（Phase B + CEO CP1,CP2 通過後）
- 05_batch_backfill.md — 段階backfill（100件→残り全件）

### Phase D（Phase C完了後）
- 06_matching_hardfilter.md — マッチングhard filter有効化

## ガードレール（全タスク共通）
1. 抽出ロジック変更とバックフィルを同じcommitに混ぜない
2. mass writeは必ず dry-run → diff log → batch-id → rollback path
3. マッチング変更はshadow mode + pilot通過後のみ
4. LLMはフォールバック限定（regex優先）
5. 空欄は埋める、非空欄は上書きしない（confidence比較でのみ上書き許可）
6. CostGuard制約: LLM抽出は1日100-150コール上限

## 依存関係図
T1 ──┐
T2 ──┼──→ T4 ──→ T5(CP1) ──→ T6(CP2) ──→ T7 ──→ T8(CP3)
T3 ──┘
"""

# ================================================================
# Task 1: Baseline + Golden Set
# ================================================================
t1 = f"""【Cursor作業指示】
対象ディレクトリ: ses_work/
作業内容: ベースライン凍結 + 60件ゴールデンセット作成
参照ファイル: CLAUDE.md / mail_pipeline/skill_extractor.py / matching_v3/
完了条件: golden_test/ ディレクトリに60件テスト fixtures + 回帰テストスクリプト完成

## 背景
精度改善R1-R4完了。R5でrate/remote/location抽出を追加する前に、現状の品質をベースラインとして凍結する。

## 作業内容

### 1. gitタグ作成
```
git tag pre_r5_stable -m "R1-R4 stable baseline before R5 extraction changes"
```

### 2. 60件ゴールデンセット作成
ファイル: `golden_test/golden_cases.json`

Notion案件DB（ID: 343450ff-37c0-81e4-934e-f25f90284a3c）から以下の層別サンプリングで60件取得:

**A群: 30件ミニベンチマーク（手動アノテーション対象）**
- 単価帯別: 明示的レンジ6件 / MAX型4件 / スキル見合い(数値なし)4件 / スキル見合い+MAX 4件 / 単価記載なし4件 / 曖昧2件
- リモート別: フルリモート5件 / ハイブリッド5件 / 常駐5件 / 曖昧リモート5件 / 言及なし5件 / 条件付き5件（重複OK）
- スキル別: バックエンド10件 / フロント5件 / インフラ5件 / PM/PMO 5件 / その他5件

**B群: 20件 R1-R4確認済み正常ケース**
- 必要スキル正常抽出済み + 単価正常 + 勤務地あり の案件から20件ランダム

**C群: 10件エッジケース**
- 0万案件3件 / ERROR履歴あり3件 / スキル空2件 / 詳細文が極端に短い2件

### 3. 各ケースのデータ構造
```json
{{
  "case_id": "notion_page_id",
  "source_text": "案件詳細の全文",
  "group": "A|B|C",
  "current_values": {{
    "required_skills": [...],
    "preferred_skills": [...],
    "rate_man": number|null,
    "location": "string|null",
    "remote_type": null
  }},
  "gold_labels": {{
    "rate_min_man": number|null,
    "rate_max_man": number|null,
    "rate_type": "fixed_range|fixed_upper_only|skill_dependent_with_cap|skill_dependent_no_number|not_present|unknown",
    "remote_type": "full_remote|hybrid|onsite|remote_possible|unknown",
    "location": "string|null",
    "required_skills_normalized": [...],
    "preferred_skills_normalized": [...]
  }}
}}
```
※ gold_labelsはA群のみ手動記入。B群C群はcurrent_valuesのスナップショットのみ。

### 4. 回帰テストスクリプト
ファイル: `golden_test/regression_test.py`

```python
# 入力: golden_cases.json + 抽出関数
# 出力: 
#   - A群: field別 precision/recall/F1
#   - B群: 既存値との差分（変化があればNG）
#   - C群: エラーなく処理完了すればOK
# 終了コード: 0=PASS, 1=REGRESSION
```

### 5. ベースラインメトリクス記録
ファイル: `golden_test/baseline_metrics.json`
- 必要スキル空率、単価空率（修正版: 0万=空扱い）、勤務地空率、リモート空率
- マッチング平均件数、0マッチ率、50+マッチ率

## 禁止事項
- 既存の抽出ロジックを変更しない
- Notion DBのデータを書き換えない
- A群のgold_labelsは空欄で作成（松野が後で記入）

## 完了条件チェックリスト
- [ ] git tag `pre_r5_stable` 作成済み
- [ ] golden_test/golden_cases.json に60件格納
- [ ] golden_test/regression_test.py が実行可能
- [ ] golden_test/baseline_metrics.json にベースライン記録
- [ ] 既存テストが全てPASS（変更なし確認）
"""

# ================================================================
# Task 2: Notion Schema
# ================================================================
t2 = f"""【Cursor作業指示】
対象ディレクトリ: ses_work/
作業内容: Notion案件DBに新プロパティを追加 + スキーマ検証スクリプト
参照ファイル: CLAUDE.md
完了条件: 新フィールド追加済み + 検証スクリプトPASS

## 背景
rate_type / remote_type等の新フィールドを案件DBに追加する。既存ページ・パイプラインを壊さないこと。

## 追加するプロパティ（案件DB: 343450ff-37c0-81e4-934e-f25f90284a3c）

| プロパティ名 | 型 | 選択肢 |
|---|---|---|
| rate_type | select | fixed_range / fixed_upper_only / skill_dependent_with_cap / skill_dependent_no_number / not_present / unknown |
| remote_type | select | full_remote / hybrid / onsite / remote_possible / unknown |
| extraction_method | select | regex / llm / manual / legacy |
| extraction_confidence | number | 0-100 |
| pipeline_version | select | v1 / v2 |
| needs_review | checkbox | - |

## 実装

### 1. スキーマ追加スクリプト
ファイル: `scripts/add_notion_schema.py`
- Notion REST API (PATCH /v1/databases/DB_ID) で上記プロパティを追加
- 既存プロパティは一切変更しない
- 冪等性: 既に存在する場合はスキップ
- Notion-Version: 2022-06-28

### 2. スキーマ検証スクリプト
ファイル: `scripts/verify_notion_schema.py`
- 全必須プロパティの存在確認
- 型の一致確認
- select選択肢の一致確認
- 既存プロパティ（必要スキル/尚可スキル/単価（万円）/勤務地等）が残っていること確認

### 3. 既存パイプラインとの互換性テスト
- mail_pipeline.pyを変更せずにdry-run
- matching_v3を変更せずにdry-run
- 新フィールドが空でもエラーにならないことを確認

## 禁止事項
- 既存プロパティの名前変更・型変更・削除
- mail_pipeline.py / matching_v3 のコード変更
- 既存ページのデータ書き換え

## 完了条件チェックリスト
- [ ] 6プロパティ全て追加済み
- [ ] verify_notion_schema.py がPASS
- [ ] 既存パイプラインdry-runがエラーなし
"""

# ================================================================
# Task 3: Pure Extractors
# ================================================================
t3 = f"""【Cursor作業指示】
対象ディレクトリ: ses_work/extractors/
作業内容: rate/remote/location純粋関数extractor実装
参照ファイル: CLAUDE.md / research_results/wallhit_R2_technical.md / research_results/pattern_analysis.py
完了条件: 3つのextractorがユニットテストPASS + ゴールデンセット回帰テストPASS

## 背景
現在の案件DBで単価0万168件（実は抽出失敗）、リモート0%、勤務地29%空。
原文にデータがあるのに抽出できていない。純粋関数として3つのextractorを新規実装する。

## 設計原則
- 全extractor は**純粋関数**（副作用なし、Notion書き込みなし）
- 入力: テキスト文字列
- 出力: 型付き結果オブジェクト（値 + メタデータ）
- regex優先、LLMフォールバックはhookのみ（実行はしない）

## 1. rate_extractor.py

### 入力
```python
def extract_rate(text: str) -> RateResult:
```

### 出力型
```python
@dataclass
class RateResult:
    rate_min_man: float | None
    rate_max_man: float | None
    rate_type: str  # fixed_range / fixed_upper_only / fixed_lower_only / skill_dependent_with_cap / skill_dependent_no_number / not_present / unknown
    confidence: float  # 0.0-1.0
    method: str  # regex / llm
    evidence: str | None  # 原文から抽出した該当箇所
    needs_llm_fallback: bool
```

### 処理順序（Pass 1→2→3）

**Pass 1: regex抽出**（優先度順に試行、最初にマッチしたものを採用）

1. スキル見合い + 数値: `スキル見合い.*?(MAX|上限|〜|~|～)\\s*(\\d{{2,3}})\\s*万`
   → rate_type=skill_dependent_with_cap, rate_max_man=数値
2. レンジ: `(\\d{{2,3}})\\s*万?\\s*[〜～\\-~]\\s*(\\d{{2,3}})\\s*万`
   → rate_type=fixed_range, min/max設定
3. MAX/上限: `(?:MAX|上限|まで|〜|~|～)\\s*(\\d{{2,3}})\\s*万`
   → rate_type=fixed_upper_only, rate_max_man=数値
4. 単純数値（単価/予算/金額の文脈内）: `(?:単価|予算|金額)[:：]?\\s*(\\d{{2,3}})\\s*万`
   → rate_type=fixed_upper_only, rate_max_man=数値, confidence=0.75
5. スキル見合い（数値なし）: `スキル見合`
   → rate_type=skill_dependent_no_number

**Pass 2: 該当パターンなし**
→ rate_type=not_present, 全てNone

**Pass 3: LLMフォールバック判定**
テキスト内に「予算」「金額」「単価」があるがPass1で数値抽出できなかった場合:
→ needs_llm_fallback=True（実際のLLM呼び出しはここではしない）

### バリデーション
- 抽出値が200万超 → null化 + needs_review=True
- 抽出値が10万未満 → confidence半減 + needs_review=True
- min > max → swap

## 2. remote_extractor.py

### 入力/出力
```python
def extract_remote(text: str) -> RemoteResult:

@dataclass
class RemoteResult:
    remote_type: str  # full_remote / hybrid / onsite / remote_possible / unknown
    onsite_days_per_week: int | None  # ハイブリッドの場合
    initial_onsite: bool | None  # 立ち上がり出社の有無
    confidence: float
    method: str
    evidence: str | None
    needs_llm_fallback: bool
```

### regex優先度順
1. フルリモート: `フルリモート|完全リモート|フル在宅|在宅100|出社なし|出社不要`
2. ハイブリッド: `リモート併用|ハイブリッド|週(\\d).*出社|一部出社|基本リモート`
   → onsite_days_per_week=キャプチャした数値
3. 常駐: `常駐|オンサイト|出社前提|基本出社|フル出社|出社必須`
4. リモート可能（曖昧）: `リモート|テレワーク|在宅`
   → remote_type=remote_possible
5. 該当なし → unknown

### 特殊パターン
- `立ち上がり.*出社` / `初日.*出社` / `初月.*出社` → initial_onsite=True
- 矛盾検出（フルリモート + 常駐 が両方ある）→ needs_llm_fallback=True

## 3. location_extractor.py
※ 既存のses_work/mail_pipeline/location_extractor.pyをベースに、同じインターフェースに合わせる。

### 入力/出力
```python
def extract_location(text: str) -> LocationResult:

@dataclass
class LocationResult:
    location: str | None  # 正規化された勤務地
    station: str | None  # 最寄駅
    area: str | None  # エリア（東京都/神奈川県等）
    confidence: float
    method: str
    evidence: str | None
```

### 正規化ルール
- 「東京都○○区」→ 区まで保持
- 「○○駅」→ 駅名保持
- 「都内」「首都圏」→ そのまま保持
- 「リモート」のみで勤務地なし → None

## テスト

### ユニットテスト: extractors/test_extractors.py
- 各パターンの正常系テスト
- エッジケース（空文字、巨大テキスト、矛盾パターン）
- 既知の0万案件からのサンプルテスト

### 回帰テスト統合
- golden_test/regression_test.py にextractor結果を追加比較

## 禁止事項
- Notion API呼び出し
- ファイルI/O（入力テキストを直接受け取る）
- LLM API呼び出し（needs_llm_fallbackフラグ設定のみ）
- mail_pipeline.py / matching_v3 の変更

## 完了条件チェックリスト
- [ ] extractors/rate_extractor.py 実装完了
- [ ] extractors/remote_extractor.py 実装完了
- [ ] extractors/location_extractor.py 実装完了（既存ベース統合）
- [ ] extractors/test_extractors.py 全テストPASS
- [ ] golden_test/regression_test.py PASS（既存値に変化なし）
"""

# ================================================================
# Task 4: Merge Policy + Backfill Engine + Shadow Mode + Pilot
# ================================================================
t4 = f"""【Cursor作業指示】
対象ディレクトリ: ses_work/
作業内容: マージポリシー + backfillエンジン + shadow mode pipeline統合 + 20件pilot
参照ファイル: CLAUDE.md / extractors/ / scripts/verify_notion_schema.py
完了条件: dry-run成功 + shadow mode稼働 + 20件pilot完了 + rollback確認済み

## 背景
Task1-3で作った extractors を安全にNotionに反映する仕組み。
最大リスクは「既存の良いデータを上書きして壊す」こと。

## 1. マージポリシー: scripts/merge_policy.py

### フィールド別ルール
```python
MERGE_RULES = {{
    # 空欄は埋める
    "fill_if_empty": ["rate_type", "remote_type", "勤務地"],
    # confidence比較で高い方を採用（非空欄の上書き）
    "replace_if_higher_confidence": ["単価（万円）"],
    # 絶対に上書きしない
    "never_overwrite": ["必要スキル", "尚可スキル", "案件詳細", "案件名"],
    # needs_reviewフラグのみ設定
    "flag_only": ["extraction_confidence", "needs_review"]
}}
```

### 判定関数
```python
def should_update(field_name, old_value, new_value, new_confidence, old_confidence=None) -> tuple[bool, str]:
    # Returns: (update_yes_no, reason)
```

## 2. Backfillエンジン: scripts/backfill_engine.py

### CLI
```
python scripts/backfill_engine.py [options]
  --dry-run          差分表示のみ、書き込みなし
  --limit N          処理件数制限
  --batch-id ID      バッチ識別子（ロールバック用）
  --only-empty       空フィールドのみ対象
  --fields FIELDS    対象フィールド（rate,remote,location）
  --page-ids IDS     特定ページのみ
```

### 処理フロー
1. Notion案件DB（募集中）を取得
2. 各ページの案件詳細テキストを取得
3. extractors で抽出
4. merge_policy で更新判定
5. dry-run: 差分をCSV/JSON出力
6. 実行モード: Notion API PATCH + 変更ログ記録

### 変更ログ: backfill_logs/BATCH_ID.json
```json
[{{
  "page_id": "xxx",
  "batch_id": "20260626_001",
  "timestamp": "2026-06-26T10:00:00",
  "changes": [
    {{"field": "rate_type", "old": null, "new": "fixed_upper_only", "reason": "fill_if_empty"}},
    {{"field": "単価（万円）", "old": 0, "new": 65, "reason": "replace_zero_with_extracted"}}
  ]
}}]
```

### ロールバック: scripts/rollback_backfill.py
```
python scripts/rollback_backfill.py --batch-id 20260626_001
```
変更ログから逆操作を実行。

### 自動停止条件
- needs_review率 > 5% → 停止+警告
- 書き込みエラー率 > 2% → 停止+警告
- 非空欄上書き検出 → 停止+警告（merge_policy違反）

## 3. Shadow Mode統合: mail_pipeline.py への追加

### 変更内容
mail_pipeline.pyの構造化処理の**後**に、v2 extractorを追加実行:
```python
# 既存の構造化処理（変更なし）
structured = existing_structurer(email_text)

# v2 extraction（shadow mode: 新フィールドにのみ書き込み）
from extractors.rate_extractor import extract_rate
from extractors.remote_extractor import extract_remote
from extractors.location_extractor import extract_location

rate_result = extract_rate(email_text)
remote_result = extract_remote(email_text)
location_result = extract_location(email_text)

# 新フィールドにのみ書き込み（既存フィールドは変更しない）
shadow_fields = {{
    "rate_type": rate_result.rate_type,
    "remote_type": remote_result.remote_type,
    "extraction_method": rate_result.method,
    "extraction_confidence": int(min(rate_result.confidence, remote_result.confidence) * 100),
    "pipeline_version": "v2"
}}
# 勤務地が空の場合のみ埋める
if not existing_location:
    shadow_fields["勤務地"] = location_result.location

# 単価0万の場合のみ修正
if existing_rate == 0 and rate_result.rate_max_man:
    shadow_fields["単価（万円）"] = rate_result.rate_max_man
elif existing_rate == 0 and rate_result.rate_type == "not_present":
    shadow_fields["単価（万円）"] = None  # 0→NULL
```

### 重要: 既存ロジックへの変更ゼロ
- 既存の必要スキル/尚可スキル抽出は一切触らない
- 既存の分類ロジックは一切触らない
- 追加の処理を末尾に足すだけ

## 4. 20件Pilot Backfill

### 手順
1. `python scripts/backfill_engine.py --dry-run --limit 20 --batch-id pilot_001`
2. 出力を確認（diff CSV）
3. `python scripts/backfill_engine.py --limit 20 --batch-id pilot_001`
4. Notion上で5件手動確認
5. rollbackテスト: 1件に対して `python scripts/rollback_backfill.py --batch-id pilot_001 --page-id XXX`

## テスト
- golden_test/regression_test.py PASS（R1-R4品質維持確認）
- backfill dry-run 出力が妥当
- rollback が正常動作

## 禁止事項
- 既存の必要スキル/尚可スキル抽出ロジック変更
- 既存の分類ロジック変更
- dry-runなしでの本番backfill実行
- rollback機能なしでのbackfill実行

## 完了条件チェックリスト
- [ ] scripts/merge_policy.py 実装完了
- [ ] scripts/backfill_engine.py --dry-run 動作確認
- [ ] scripts/rollback_backfill.py 動作確認
- [ ] mail_pipeline.py にshadow mode統合済み
- [ ] 20件pilot backfill完了
- [ ] backfill_logs/pilot_001.json に変更ログ記録
- [ ] golden_test/regression_test.py PASS
- [ ] ★ この時点で松野に報告（CEO Checkpoint 1+2）
"""

# ================================================================
# Task 5: Batch Backfill
# ================================================================
t5 = f"""【Cursor作業指示】
対象ディレクトリ: ses_work/
作業内容: 段階backfill（100件→残り全件）
参照ファイル: CLAUDE.md / scripts/backfill_engine.py
完了条件: 全募集中案件のbackfill完了 + メトリクス改善確認
前提: Task4のCEOチェックポイント通過済み

## 手順

### Step 1: 100件バッチ
```
python scripts/backfill_engine.py --dry-run --limit 100 --batch-id batch_100
# dry-run確認
python scripts/backfill_engine.py --limit 100 --batch-id batch_100
```
- 自動停止条件に引っかからないこと確認
- needs_review件数を記録

### Step 2: 残り全件
```
python scripts/backfill_engine.py --batch-id batch_remaining
```
- LLMフォールバックは1日100コール上限（CostGuard）
- needs_llm_fallback=Trueの案件は別途キューイング

### Step 3: ERROR案件再処理（1,509件）
```
python scripts/backfill_engine.py --status ERROR --batch-id error_retry --fields rate,remote,location
```
- ERRORの再分類はここではやらない（extractionのみ）
- pipeline_version=v2 でタグ付け

### Step 4: メトリクス再計測
```
python golden_test/regression_test.py --report
```
出力: 改善前後の比較表

## 完了条件チェックリスト
- [ ] 100件バッチ完了、自動停止なし
- [ ] 残り全件完了
- [ ] ERROR案件再処理完了
- [ ] 改善メトリクス記録済み
- [ ] LLM使用額がCostGuard内（$8/day, $140/month）
"""

# ================================================================
# Task 6: Matching Hard Filter
# ================================================================
t6 = f"""【Cursor作業指示】
対象ディレクトリ: ses_work/matching_v3/
作業内容: マッチングhard filter実装
参照ファイル: CLAUDE.md / SPEC.md / research_results/wallhit_R2_technical.md
完了条件: avg matches 128.5→5-15 + ベンチマークPASS + config toggleで個別ON/OFF可能

## 背景
現在matching_v3はavg 128.5マッチ（多すぎ）。rate/remote/locationの抽出品質が上がったので、hard filterで絞り込む。

## フィルタ実装順序

### Filter 1: ステータスゲート
- 募集中以外を除外（既にある場合はスキップ）

### Filter 2: 単価互換性
```python
def rate_compatible(case, engineer) -> bool:
    if case.rate_max_man is None:
        return True  # 不明は通す
    if case.rate_type == "skill_dependent_no_number":
        return True  # スキル見合いは通す
    if engineer.desired_rate_min is None:
        return True  # エンジニア側不明は通す
    # エンジニア希望最低 > 案件MAX + 3万 → 不適合
    return engineer.desired_rate_min <= case.rate_max_man + 3
```

### Filter 3: リモート/勤務地互換性
```python
def location_compatible(case, engineer) -> bool:
    if case.remote_type == "full_remote":
        return True  # フルリモートは全員OK
    if case.remote_type == "unknown":
        return True  # 不明は通す
    # 常駐/ハイブリッド → エンジニアの通勤可能エリアと照合
    # エンジニア側に勤務地データがない場合は通す
    if not engineer.commutable_areas:
        return True
    return case.location_area in engineer.commutable_areas
```

### Filter 4: 必須スキル閾値
```python
def skill_compatible(case, engineer) -> bool:
    if not case.required_skills:
        return True
    required = set(normalize_skills(case.required_skills))
    engineer_skills = set(normalize_skills(engineer.skills))
    overlap = required & engineer_skills
    if len(required) == 1:
        return len(overlap) >= 1  # 1スキルなら完全一致必須
    return len(overlap) / len(required) >= 0.5  # 2+なら50%以上
```
※ normalize_skills は skill_aliases.json を使用

### Filter 5: 開始時期
- 案件の開始月とエンジニアの稼働可能月を比較
- データがない場合は通す

## config toggle
```python
# matching_v3/config.py
HARD_FILTERS = {{
    "rate": True,
    "remote_location": True,
    "skill_threshold": True,
    "start_timing": True,
}}
```
個別にON/OFFできること。

## 計測
- フィルタ別のdrop-off率を記録
- before/afterのavg match count比較
- ゴールデンセットでのfalse negative率

## 禁止事項
- LLMスコアリングの追加（ルールベース維持）
- エンジニアDBのデータ変更
- 既存のスキルマッチングロジック削除（filterは追加のみ）

## 完了条件チェックリスト
- [ ] 4フィルタ実装完了
- [ ] config toggleで個別ON/OFF動作確認
- [ ] avg match count: 128.5 → 目標5-15
- [ ] false negative率 < 5%（ベンチマーク）
- [ ] フィルタ別drop-off率のレポート出力
- [ ] ★ 松野に最終レポート報告（CEO Checkpoint 3）
"""

# ================================================================
# Write all files
# ================================================================
files = {
    f"00_ORCHESTRATION_R5_accuracy.md": orch,
    f"01_{ts}_baseline_golden_set.md": t1,
    f"02_{ts}_notion_schema.md": t2,
    f"03_{ts}_extractors.md": t3,
    f"04_{ts}_merge_shadow_pilot.md": t4,
    f"05_{ts}_batch_backfill.md": t5,
    f"06_{ts}_matching_hardfilter.md": t6,
}

for fname, content in files.items():
    fpath = os.path.join(PENDING, fname)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Created: {fname}")

print(f"\nTotal: {len(files)} files in pending_tasks/")
print("DONE")
