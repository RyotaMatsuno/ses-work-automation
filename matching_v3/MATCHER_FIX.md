# matcher.py 修正タスク

## 問題
`judge()` 関数で、`normalizer.normalize(skill)` がNoneを返す
（= skill_aliases.json に未登録のスキル）場合に
`reasons.append(f"未知スキル（要確認）: {skill}")` して最終的に REVIEW になる。

SES案件では「SQL」「要件定義」「基本設計」等のスキルが頻出するが、
エンジニアDB の `スキル` フィールドは言語/技術スタックのみ登録されている。
「未知スキル」が量産されて全ペアが REVIEW になっている。

## 修正内容（matcher.py）

`judge()` 関数内の以下のコード:
```python
elif not normalized:
    reasons.append(f"未知スキル（要確認）: {skill}")
```

を削除する（コメントアウトでなく完全削除）。

未知スキルは REVIEW 理由にしない。既存の required_skills チェックは
「正規化できたスキルが engineer のスキルリストにない場合のみ NG」とする。

修正後のループは:
```python
for skill in required_raw:
    normalized = normalizer.normalize(skill)
    if normalized and normalized not in eng_skills:
        missing.append(normalized)
    # normalized が None の場合（未知スキル）は何もしない
if missing:
    return "NG", [f"必須スキル不足: {missing}"]
```

## テスト
- 既存の pytest 17件が全パスすること
- 特に `test_ng_required_skill_missing` が通ること（Javaは登録済みなのでそのままNGになる）

## 注意
- CLAUDE.md / SPEC.md のルールに従うこと
- 認証情報は変更しないこと
- 完了したらこのファイルに [DONE] を追記

[DONE]
