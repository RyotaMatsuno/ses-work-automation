# 【Cursor作業指示】Task AY: mail_pipeline→Notion保存パイプライン修正+バックフィル

対象: ses_work/mail_pipeline.py + ses_work/matching_v3/structurer.py
参照: CLAUDE.md / mail_pipeline.py
完了条件: 新規案件登録時に必須スキルがmulti_selectに自動保存される + 既存案件のバックフィル

---

## 背景
structurer.pyがメールからスキルを抽出しているが、mail_pipeline.pyがNotionに保存する際に
必須スキル(multi_select)フィールドに反映されていない（推定）。
結果、案件DBの60%がスキル空の状態。

## 調査: 保存フローの確認
1. mail_pipeline.pyでNotion案件DBにページを作成する箇所を特定
2. structurer.pyの出力JSON（required_skills等）がどこに渡されているか追跡
3. Notion APIのmulti_select保存フォーマットを確認:
```python
# multi_selectへの保存形式
"必要スキル": {
    "multi_select": [
        {"name": "Java"},
        {"name": "AWS"},
        {"name": "Spring"}
    ]
}
```

## 修正1: 新規保存フロー修正
mail_pipeline.py → Notion案件DB保存時に:
- structurer出力のrequired_skills → 必要スキル(multi_select)
- structurer出力のpreferred_skills → 尚可スキル(multi_select)
- structurer出力のrate_min/rate_max → 単価（万円）(number)
- structurer出力のlocation → 勤務地(rich_text)

multi_selectに保存する前に、各スキル名をskill_aliases.jsonで正規化し、
canonical名で保存する（表記ゆれ防止）。

## 修正2: 既存案件バックフィル
scripts/backfill_case_skills.py 新規作成:
- Notion案件DBから必須スキル空の案件を全件取得
- 各案件の案件名 + 案件詳細 + 案件情報原文からスキルをルールベース抽出
- skill_aliases.json(182語)で照合
- --dry-runでプレビュー → 実行で必須スキルmulti_selectに保存
- 保存時にsource='backfill'タグを備考に追記（手動登録と区別）

## 修正3: 保存時バリデーション
案件登録時の警告:
- 案件名にスキル語があるのに必須スキルmulti_select空 → warning log
- 単価が空 → warning log
- 案件詳細が空 → warning log

## テスト
- 新規案件保存で必須スキルが正しくmulti_selectに入ること
- バックフィルのdry-run出力が妥当なこと
- バリデーション警告が正しく出ること

## 禁止
- CostGuardなしでLLMを呼び出さない
- 既存案件の案件名や案件詳細を書き換えない（スキルフィールドのみ追記）
