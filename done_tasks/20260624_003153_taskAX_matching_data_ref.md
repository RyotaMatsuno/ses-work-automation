# 【Cursor作業指示】Task AX: matching_v3のNotion参照修正+空値フォールバック（最優先）

対象: ses_work/matching_v3/
参照: CLAUDE.md / matching_v3.py / matcher.py / notion_client.py
完了条件: 必須スキル空の案件でもマッチング判定が動作する

---

## 背景（実データ検証で判明）
- Notion案件DBの必須スキル(multi_select)が**60%空**
- エンジニアDBのスキル(multi_select)はPHP,Java等が入っている
- エンジニアDBの単価(number)も入っている（例: 40万、63万）
- しかしmatching_v3がこれらを正しく参照できているか不明

## 調査1: 現在の参照ロジックの確認
1. matching_v3.py / notion_client.py でNotionからケース・エンジニアを取得する箇所を特定
2. 各Notionプロパティ名と取得ロジックを洗い出す:

案件DB確認すべきプロパティ:
| プロパティ | 型 | 用途 |
|---|---|---|
| 案件名 | title | 案件タイトル |
| 必要スキル | multi_select | ★必須スキル |
| 尚可スキル | multi_select | 尚可スキル |
| 単価（万円）| number | 案件予算 |
| 仕入単価（万円）| number | 仕入れ単価 |
| 勤務地 | rich_text | 勤務地 |
| リモート | select | リモート可否 |
| 年齢制限 | rich_text | 年齢制限（自由記述） |
| 案件詳細 | rich_text | フルテキスト |
| 案件情報原文 | rich_text | メール原文 |

エンジニアDB確認すべきプロパティ:
| プロパティ | 型 | 用途 |
|---|---|---|
| スキル | multi_select | ★技術スキル |
| 単価（万円）| number | 希望単価 |
| 国籍 | select | 日本/外国 |
| 稼働状況 | select | 稼働可能/稼働中 |
| 稼働可能日 | date | 開始可能日 |
| 居住地 | select | 居住エリア |
| 経験年数 | number | 経験年数 |
| 情報取得日 | date | 鮮度計算用 |

## 修正1: 空値フォールバック
案件の必須スキルが空の場合のフォールバックチェーン:
```
1. 必要スキル(multi_select) → メインソース
2. 空なら → 案件名(title)からルールベース抽出
3. それも空なら → 案件詳細(rich_text)からルールベース抽出
4. それも空なら → 案件情報原文(rich_text)からルールベース抽出
```

ルールベース抽出: skill_aliases.jsonのcanonical_skills(182語)を案件名/詳細から検索
```python
def extract_skills_from_text(text: str, normalizer: SkillNormalizer) -> list[str]:
    found = []
    for canonical in normalizer.all_canonicals():
        if canonical.lower() in text.lower():
            found.append(canonical)
    # alias逆引きも実行
    for alias, canonical in normalizer.all_aliases():
        if alias.lower() in text.lower():
            if canonical not in found:
                found.append(canonical)
    return found
```

## 修正2: エンジニアスキル参照の一本化
- multi_select「スキル」を主ソースとする
- matching_v3がrich_textの「スキル」ではなくmulti_selectの「スキル」を参照していることを確認
- multi_selectの各値をskill_aliases.jsonで正規化

## 修正3: 参照ログ追加
judge()呼び出し前にログ出力:
```
DEBUG case=xxx required_skills=[Java, AWS] source=multi_select
DEBUG case=xxx required_skills=[Java] source=fallback_title
DEBUG eng=YS skills=[PHP, Java, SQL] price=40
```

## テスト
- 必須スキル空の案件 → フォールバックで案件名からスキル抽出 → judge()実行
- 必須スキルあり → そのままjudge()
- エンジニアmulti_selectからスキル正常取得
- 単価の正常取得確認

---

## 完了メモ (2026-06-24)
- `matcher.py`: `extract_skills_from_text`, `resolve_case_required_skills`, `prepare_engineer_skills`, `canonicalize_skill_list`, `log_case_skills_debug`, `log_engineer_match_debug`
- `SkillNormalizer`: `all_canonicals()`, `all_aliases()` 追加
- `notion_client.py`: 案件/エンジニアの不足プロパティをパース追加
- `matching_v3.py`: フォールバック適用・Notion単価/尚可スキル補完・judge前DEBUGログ
- `tests/test_task_ax_matching_data_ref.py` 8件パス、matching_v3全190件パス
