# 【Cursor作業指示】Task AM: structurer.py抽出精度改善

対象: ses_work/matching_v3/
参照: CLAUDE.md / structurer.py / skill_aliases.json
完了条件: 構造化JSONの必須フィールド充足率80%以上

## 変更
1. LLMプロンプト改善:
   - 出力スキーマを厳格化: required_skills[], preferred_skills[], rate_min, rate_max, location, remote_ratio
   - 「推測禁止・原文から抽出できないものはnull」を明示
   - few-shot例を3件→5件に増強（特に単価レンジ、スキル分離の例）
2. 後処理追加:
   - LLM出力のrequired_skillsをskill_aliases.jsonで正規化
   - 「Java/Spring」→「Java」「Spring」に分割するスプリッタ
   - rate_min/rate_maxが文字列で返った場合の数値変換
   - required_skillsが空の場合、件名からルールベース抽出にフォールバック
3. extraction_confidenceの計算改善:
   - 必須フィールド(required_skills, rate, location)の充足率で算出
   - confidence < 0.3 の案件は構造化失敗としてフラグ

## テスト
- 既存test_structurer.pyのテスト全合格
- 新規テスト: スキル分割、数値変換、confidence計算
