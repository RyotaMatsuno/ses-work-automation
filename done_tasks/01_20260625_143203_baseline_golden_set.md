【Cursor作業指示】
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
{
  "case_id": "notion_page_id",
  "source_text": "案件詳細の全文",
  "group": "A|B|C",
  "current_values": {
    "required_skills": [...],
    "preferred_skills": [...],
    "rate_man": number|null,
    "location": "string|null",
    "remote_type": null
  },
  "gold_labels": {
    "rate_min_man": number|null,
    "rate_max_man": number|null,
    "rate_type": "fixed_range|fixed_upper_only|skill_dependent_with_cap|skill_dependent_no_number|not_present|unknown",
    "remote_type": "full_remote|hybrid|onsite|remote_possible|unknown",
    "location": "string|null",
    "required_skills_normalized": [...],
    "preferred_skills_normalized": [...]
  }
}
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
