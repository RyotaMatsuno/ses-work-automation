# 【Cursor作業指示】Task AN: matching_v3高速化

対象: ses_work/matching_v3/
参照: CLAUDE.md / matching_v3.py / matcher.py
完了条件: 全案件処理時間を50%以上短縮

## 変更
1. エンジニアスキルの逆引きインデックス構築:
   - 起動時に skill -> set(engineer_id) のinverted indexを作成
   - 案件のrequired_skillsからcandidate engineer_idを事前絞り込み
   - required_skillsが空の場合のみ全エンジニアを対象
2. 鮮度フィルタ（AJ）を候補抽出の最初に適用し、無駄な judge() 呼び出しを削減
3. 差分実行:
   - processed_casesで既にmatched/ngの案件はスキップ
   - 案件のlast_edited_atが前回マッチング以降に更新された場合のみ再処理
4. 並列judge()実行:
   - ThreadPoolExecutor(max_workers=4)でjudge()を並列化
   - CostGuardのスレッドセーフ確認

## 計測
- 改修前後のログで処理時間を比較
- 「処理案件数」「スキップ案件数」「候補絞込前後の件数」をログ出力
