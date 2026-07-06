# Phase5 TASKS

- [x] matching_v3/matcher.py: judge()の単価チェックを粗利5万床に変更
- [x] matching_v3/matcher.py: judge()の未知必須スキル処理をREVIEW要因に変更  
- [x] matching_v3/matcher.py: judge()の並行スコア>=5.0をNGに変更
- [x] matching_v3/notion_client.py: get_active_engineers()のfilterに提案対象フラグ追加（try-except対応）
- [x] py_compile で matcher.py と notion_client.py の構文確認


## 追加タスク（GPT-5.4壁打ち反映）

- [x] judge()の粗利判定を3値化（PASS/NG/REVIEW）— 推定単価のみでNG禁止
- [x] judge()に engineer_unit_price_source / gross_profit_calc_status ログ追加
- [x] judge()の未知スキルを必須/尚可で分離（尚可のみ未知はINFO）
- [x] judge()の並行スコア欠損時にREVIEW（NG禁止）
- [x] get_active_engineers()のfilter例外時はfail-open + WARNING log
- [x] テスト追加: 単価欠損時にREVIEW判定されること
- [x] テスト追加: 推定単価のみで粗利不足時にREVIEW（NG不可）
- [x] テスト追加: 並行スコアNone時にREVIEW判定されること
- [x] テスト追加: filter例外時にfail-openで全件通ること（notion_clientのfail-open動作で担保）
- [x] judge_version="v5.1" を判定結果に記録
