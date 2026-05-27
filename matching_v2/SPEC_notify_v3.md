# SPEC: notify_line.py v3 — フル情報表示・会社名表示対応

## 目的
LINEマッチング通知に案件・人員のフル情報と所属会社名を表示する。

---

## 修正対象
`ses_work/matching_v2/notify_line.py`

---

## 修正要件

### 1. 案件フル情報表示
`build_project_message()` の案件セクションに以下を全て表示する。
現在の `detail` だけでなく、Notionから取得できる全フィールドを表示。

表示項目（順番通り）:
```
【マッチング結果】
案件: {案件名}  ← 既存
案件URL: {notion_url}  ← result.jsonの project_url を使う（Notion未取得でもURLは持っている）
入力元（会社名）: {input_source} / {affiliation}  ← どちらかあれば表示
業務内容: {detail}
必須スキル: {required_skills}
尚可スキル: {optional_skills}
単価: {price}万円
稼働: {start_date}
勤務地: {location}
リモート: {remote}
面談: {interview_count}回
外国籍: {foreign_ok}
──────────────
```

### 2. Notionから取得する案件フィールド追加
`get_page_info()` の `page_type == "project"` ブロックに以下を追加:

```python
"location": get_text_property(props, "勤務地"),
"remote": get_text_property(props, "リモート"),
"interview_count": get_text_property(props, "面談回数"),
"foreign_ok": get_text_property(props, "外国籍"),
"period": get_text_property(props, "期間"),
```

`empty_page_info("project")` にも同じキーを追加（空文字で）。

### 3. 人員フル情報表示
各候補者の表示に以下を追加:

```
▶ {engineer_name}（スコア: {score}）{needs_check_warning}
  所属会社: {affiliation}  ← affiliationがあれば表示
  入力元: {input_source}
  単価: {price}万円 / 稼働: {available_date}
  スキル: {skills}
  必須判定: {required_judgement_with_reason}  ← result/reasonを両方表示
  尚可判定: {optional_judgement_with_reason}
```

### 4. 判定理由を表示する
現在の `format_judgement()` はresultのみ表示。reasonも含めて表示する。

変更後:
```python
def format_judgement(judgement):
    if not judgement:
        return "なし"
    parts = []
    for skill, value in judgement.items():
        if isinstance(value, dict):
            result = value.get("result", "")
            reason = value.get("reason", "")
            parts.append(f"{skill}:{result}（{reason}）")
        else:
            parts.append(f"{skill}:{value}")
    return "\n    ".join(parts)  # 複数スキルは改行インデント
```

### 5. 案件URLをresult.jsonから直接使う
Notionへのfetchに失敗しても、`result.json`の`project_url`/`engineer_url`は常にある。
`get_project_id()`の後、`item.get("project_url", "")`をproject_infoの`url`キーに格納して表示。

```python
project_info["url"] = item.get("project_url", "")
```

各エンジニアも同様:
```python
engineer_info["url"] = candidate.get("engineer_url", "")
```

表示:
```
案件URL: {url}
...
  NotionURL: {engineer_url}
```

---

## 変更しないこと
- 担当者判定ロジック（Notionの担当者フィールド参照）
- push_message()のLINE送信ロジック
- dry-runオプション
- 4ケース通知ロジック（build_notifications）
- sort（LINE案件を先に表示）

---

## バックアップ
修正前に `notify_line.py` を `notify_line.py.bak_v3` としてコピーしてから修正すること。

---

## テスト
修正後に dry-run で動作確認:
```
python matching_v2/notify_line.py --dry-run
```
エラーなく出力されること。出力に `業務内容:` `勤務地:` `所属会社:` `理由` が含まれることを確認。
