【Cursor作業指示】
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
HARD_FILTERS = {
    "rate": True,
    "remote_location": True,
    "skill_threshold": True,
    "start_timing": True,
}
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


## RETRY 1 REASON
exit=1 / stderr=
