
# SPEC.md - webhook_server.py 2バグ修正

## 修正1: 外国籍チェックの追加

### 対象関数
`validate_engineer_for_registration(info, raw_text)` (718行目付近)

### 修正内容
name チェックの直後（pref チェックの前）に以下を追加する：

```python
# 外国籍チェック
nationality = str(info.get("nationality") or info.get("note") or "").lower()
raw_lower = (raw_text or "").lower()
foreign_keywords = ["外国籍", "中国", "韓国", "ベトナム", "インド", "フィリピン", "ネパール", 
                    "バングラ", "パキスタン", "スリランカ", "ミャンマー", "インドネシア",
                    "chinese", "korean", "vietnamese", "indian", "foreign"]
for kw in foreign_keywords:
    if kw in nationality or kw in raw_lower:
        print(f"[SKIP] foreign nationality: {kw} / {(raw_text or '')[:100]}")
        return False, "foreign_nationality"
```

また `register_engineer` 内の `valid, skip_reason` チェック後の返信処理に
`"foreign_nationality"` ケースを追加する（既存の `area_out_of_scope` の隣）：

```python
elif skip_reason == "foreign_nationality":
    reply_message(reply_token, "外国籍のため登録をスキップしました", sender_token)
    return
```
※ reply_token が使える文脈かどうか確認してから追加すること。使えない場合はログ出力のみ。

---

## 修正2: classify_sheet_content のプロンプト強化

### 対象関数
`classify_sheet_content(text)` (259行目付近)

### 修正内容
systemプロンプトを以下に差し替える：

```python
system = '''You are a classifier for SES (System Engineer Staffing) business documents in Japanese.
Classify the content as "engineer" (skill sheet / resume / 経歴書 / スキルシート) 
or "project" (job requirement / 案件 / 求人 / 募集要項).

Rules:
- If it contains person name, work history, skill list, self-introduction → "engineer"
- If it contains required skills, job description, client info, contract period → "project"  
- When unclear, default to "engineer"

Reply JSON only: {"content_type": "engineer"} or {"content_type": "project"}'''
```
