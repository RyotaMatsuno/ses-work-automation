# SPEC — Phase 6: フィルタ設計刷新（Recall@10 改善）

## 背景
- 現状0マッチ率50%→Recall上限49.6%で目標85%未達確定
- GPT-5.4壁打ち5回でGO判定済み（research_results/gpt_wallhit_precision_20260629.md）
- 根本原因: ハードフィルタが厳しすぎてエンジニア母集団が消えている

## 改善①: alias正規化強化

### 対象ファイル
- matching_v3/skill_aliases.json

### 追加するalias（高頻度・安全な語のみ）
以下は既存辞書に不足している可能性のある高頻度語を追加:

```json
追加候補（既存と重複しないもののみ）:
- "mysql8" → "MySQL"
- "postgres" → "PostgreSQL" (既存確認)
- "spring boot" → "Spring" (既存確認)
- "vue 3" → "Vue.js"
- "react 18" → "React"
- "python3" → "Python"
- "java 11" / "java 17" / "java 21" → "Java"
- "node 18" / "node 20" → "Node.js"
- "docker compose" → "Docker"
- "terraform cloud" → "Terraform"
```

### 追加ルール
- **誤統合禁止リスト（絶対に同一化しない）:**
  - Java ≠ JavaScript
  - C ≠ C# ≠ C++
  - Spring ≠ Spring Boot (親子関係はparent_skillsで管理)
  - React ≠ React Native (親子関係はparent_skillsで管理)
  - SQL ≠ MySQL ≠ PostgreSQL ≠ SQL Server
  - Vue ≠ Nuxt (親子関係)
- 正規化ログを出力: raw_skill / normalized_skill / rule_hit

### 検証方法
- 正規化前後のユニークスキル数を比較
- 直近案件の0件率を before/after で比較

## 改善②: 駅一致ハードフィルタ → 加点式

### 対象ファイル
- matching_v3/matcher.py（filter_engineers関連）
- matching_v3/config.py（HARD_FILTERS設定）

### 変更内容
config.pyの `HARD_FILTERS["remote_location"]` を False に変更。
代わりにSoft層でlocation_scoreを算出。

### location_score設計
```python
def calc_location_score(engineer_station, case_location):
    if not engineer_station or not case_location:
        return 0.0  # 不明は中立（除外しない）
    if exact_station_match(engineer_station, case_location):
        return 1.0
    if same_line(engineer_station, case_location):
        return 0.7
    if same_prefecture(engineer_station, case_location):
        return 0.2
    return 0.0  # 遠方だが除外はしない
```

### 簡易駅マスタ
- station_master.json を新規作成
- 初期版: 主要路線（JR山手線、JR中央線、東京メトロ各線、都営各線）の駅→路線マッピング
- 後で拡充可能な設計にする

## 改善③: フィルタ3層化（Hard / Soft / Rerank）

### 対象ファイル
- matching_v3/matcher.py

### 新アーキテクチャ
```
Step 1: Hard Filter（絶対条件のみ）
  - 提案対象フラグ = False → 除外
  - 稼働状況 = 稼働中 → 除外
  - 稼働開始が案件開始より3ヶ月以上後 → 除外

Step 2: Soft Scoring（全候補に点数付与）
  - skill_score: SKILL_MATCH_THRESHOLD基準（既存ロジック維持）
  - location_score: 改善②の加点式
  - experience_score: 経験年数の近似評価
  - availability_score: 稼働開始日の近接度
  - total_score = Σ(weight_i × score_i)

Step 3: Rerank + Top-N
  - total_score降順でソート
  - 上位MAX_CANDIDATES_BEFORE_JUDGE件をJudgeに送る
```

### 重み（初期値、config.pyで管理）
```python
SCORE_WEIGHTS = {
    "skill": 0.5,
    "location": 0.15,
    "experience": 0.15,
    "availability": 0.2,
}
```

### experience_score設計
```python
def calc_experience_score(engineer_years, required_years):
    if engineer_years is None or required_years is None:
        return 0.5  # 不明は中立
    diff = engineer_years - required_years
    if diff >= 0:
        return 1.0  # 要件以上
    elif diff >= -1:
        return 0.7  # 1年不足
    elif diff >= -2:
        return 0.4  # 2年不足
    else:
        return 0.1  # 3年以上不足
```

### availability_score設計
```python
def calc_availability_score(engineer_start, case_start):
    if not engineer_start or not case_start:
        return 0.5  # 不明は中立
    diff_days = (engineer_start - case_start).days
    if diff_days <= 0:
        return 1.0  # 即稼働可
    elif diff_days <= 30:
        return 0.8  # 1ヶ月以内
    elif diff_days <= 60:
        return 0.5  # 2ヶ月以内
    else:
        return 0.2  # 2ヶ月超
```

### 候補ごとのscore_breakdown出力
```python
{
    "engineer_id": "xxx",
    "scores": {
        "skill": 0.8,
        "location": 0.7,
        "experience": 1.0,
        "availability": 0.8,
        "total": 0.82
    },
    "hard_pass": true,
    "rejection_reasons": []
}
```

## KPI監視
- 0件率: 目標<15%、アラート>25%
- Hard除外率: 目標<30%、アラート>50%
- alias正規化ヒット率: 10-30%

## テスト追加
- test_filter_3layer.py: Hard/Soft/Rerankの分離テスト
- test_location_score.py: 駅加点のテスト
- test_experience_score.py: 経験年数近似のテスト
- test_availability_score.py: 稼働日近接度のテスト
