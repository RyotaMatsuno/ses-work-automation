# SPEC: REVIEW率 <30% 達成修正

## 目標
現状REVIEW=80.9% → 目標REVIEW<30%

## 現状分析
REVIEW残存理由:
1. 構造化精度低(conf=0.35): 1,725件 → conf閾値0.5がまだ厳しい
2. 曖昧スキルあり(コミュニケーション能力等): 多数 → ambiguous_skillsのみが理由でREVIEWは過剰

## タスク1: matcher.py conf閾値を0.5→0.3に緩和

ファイル: `matcher.py`
```python
# 変更前
if conf < 0.5:
# 変更後
if conf < 0.3:
```

## タスク2: matcher.py にambiguous_skills単独REVIEW抑制ロジック追加

### 問題
ambiguous_skillsのみが理由でREVIEWになるケースが大量発生。
必須スキルが全て揃っていてambiguous_skillsだけが懸念なら、
REVIEWではなくMATCH（注記付き）にすべき。

### 変更内容
`judge()`関数内で、reasonsがambiguous_skillsのみで構成される場合は
REVIEWではなくMATCHを返すよう修正する。

具体的には:
- reasonsの全要素が「曖昧スキルあり」で始まる場合 → MATCH（ambiguous注記付き）
- reasonsにconf低・並行超過・エンジニア古い等が含まれる場合 → 従来通りREVIEW

```python
# judge()の最後の部分を変更
if reasons:
    # ambiguous_skillsのみが理由の場合はMATCHとして扱う
    non_ambig = [r for r in reasons if not r.startswith("曖昧スキルあり")]
    if not non_ambig:
        return "MATCH", reasons  # ambiguous注記はreasonに残す
    return "REVIEW", reasons
return "MATCH", []
```

## タスク3: pytest実行して全pass確認

```
cd matching_v3
pytest tests/ -v
```

## 注意事項
- config.py・cost_guard.py・structurer.pyは変更しない
- テストを壊さないこと
- 変更はmatcher.pyのみ
