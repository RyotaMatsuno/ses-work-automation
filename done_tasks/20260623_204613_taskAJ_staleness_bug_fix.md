# 【Cursor作業指示】Task AJ: staleness bug修正＋鮮度フィルタ共通化（P0）

対象: ses_work/matching_v3/
参照: CLAUDE.md / staleness_checker.py / matcher.py / matching_v3.py
完了条件: 鮮度21日超のエンジニアがマッチング候補から除外される + テスト追加

## 背景
staleness_checker.pyは存在するがmatching_v3の候補抽出に正しく適用されていない（既知バグ）。
古い人材が候補に混入し、提案品質が低下している。

## 変更
1. matching_v3.py の候補抽出ループ冒頭で is_engineer_fresh() を呼び、False なら除外+ログ記録
2. staleness_checker.py の check() が返す days_old を match_results_json に含める
3. config で max_profile_age_days=21（判断マニュアルv3準拠）を外出し
4. 除外されたエンジニア数をdaily_statsに staleness_excluded_count として記録
5. テスト: 22日前更新エンジニアが除外されること、20日前が通過すること

## 禁止
- CostGuardなしでLLMを呼び出さない
- 既存NG/MATCH判定を変更しない
