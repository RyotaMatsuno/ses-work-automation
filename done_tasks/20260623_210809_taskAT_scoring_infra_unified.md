# 【Cursor作業指示】Task AT統合: スコアリング＋継続改善インフラ（ランキング・失敗収集・未知スキル発見）

対象: ses_work/matching_v3/ + ses_work/scripts/ + ses_work/logs/
参照: CLAUDE.md / matcher.py / matching_v3.py / notifier.py
完了条件: MATCH候補がスコア順ソート + 失敗/未知スキルの自動収集

---

## ■1. 鮮度スコア減衰+候補ランキング（旧Task AT）
matcher.py の judge() 戻り値を拡張:
```python
# 旧: return verdict, reasons
# 新: return verdict, reasons, score
```
スコア計算:
```python
def _calc_match_score(engineer, hit_skills, alias_hits, soft_hits, case_max, eng_price):
    score = 1.0
    # 鮮度減衰
    days = _engineer_days_old(engineer)
    if days > 14: score -= 0.2
    elif days > 7: score -= 0.1
    # スキル一致ボーナス
    score += len(hit_skills) * 0.12 + len(alias_hits) * 0.08 + len(soft_hits) * 0.04
    # 単価適合
    gross = case_max - eng_price
    if gross >= 7: score += 0.1
    elif gross < 5: score -= 0.1
    # 並行減点
    p = _calc_parallel_score(engineer)
    if p >= 3.0: score -= 0.2
    elif p >= 2.0: score -= 0.1
    return max(0.0, min(2.0, score))
```
- matching_v3.pyでMATCH候補をscore降順ソート
- match_results_jsonにscoreフィールド追加
- notifier.pyで上位3名を優先表示

## ■2. 失敗サンプル自動収集（旧Task AU）
新規: common/failure_collector.py
```python
def collect_failure(category: str, data: dict, reason: str):
    # category: "extraction_fail", "no_match", "quality_review", "partial_only"
    # logs/failure_samples/YYYY-MM-DD.jsonl に追記
    # 1日最大20件（超過はスキップ）
```
フック箇所:
- structurer.py: confidence < 0.3 → collect("extraction_fail", ...)
- matcher.py: 全候補NG → collect("no_match", case_json + 上位3 NG理由)
- matcher.py: PARTIAL_MATCHのみ → collect("partial_only", ...)

## ■3. 未知スキル候補の自動発見（旧Task AW）
新規: scripts/discover_unknown_skills.py
- matching_v3_processed.dbから直近7日のREVIEW理由を集計
- 「語彙外」「未登録」スキル名を抽出
- skill_aliases.json未登録 + 出現3回以上 → 候補
- 前後文コンテキスト3例を付与
- 出力: logs/unknown_skill_candidates/YYYY-MM-DD.json
- matching_v3.pyの日次実行後に自動呼び出し

## テスト
- score計算: 高鮮度+高スキル一致=高スコア、低鮮度+低一致=低スコア
- ソート: score降順で正しく並ぶこと
- failure_collector: 各カテゴリで収集+20件上限
- discover: 出現3回以上の未知語が抽出されること

## 禁止
- judge()のverdict判定ロジック（MATCH/REVIEW/NG）を変更しない
- CostGuardなしでLLMを呼び出さない
- 既存のテストを壊さない
