# SPEC.md - line_query

## Overview
Parse short LINE text, cross-search Notion engineer/project DBs,
return full-text match result as LINE reply string.

---

## Input Pattern Detection

### Pattern A: Engineer Query
- Condition: text matches "INITIAL(space or slash)STATION"
- Example: "TK 渋谷" / "TK/渋谷" / "tk 渋谷" (case insensitive)
- Regex: `^([A-Za-z]{1,4})[\s/](.+)$`
- Action: engineer_query(initial, station)

### Pattern B: Project Query
- Condition: does NOT match Pattern A
- Example: "Java開発_〇〇社"
- Action: project_query(text)

---

## Notion DB Definitions (ACTUAL properties confirmed 2026-05-29)

### Engineer DB
- DB ID: 343450ff-37c0-819d-8769-fb0a8a4ceeb1
- Properties used:
  - 名前 (title)
  - イニシャル (rich_text)
  - 最寄り駅 (rich_text)
  - 単価（万円） (number)
  - スキル (multi_select)
  - 稼働可能日 (date)
  - 稼働状況 (select): 稼働可能 / 調整中 / 稼働中
  - 担当者 (select): 松野 / 岡本 / 共通
  - 備考（LINEメモ） (rich_text)
  - 所属会社 (rich_text)
  - last_edited_time (system property)
  - ※ 提案対象フラグ は存在しない → 稼働状況が「稼働可能」or「調整中」の人員のみ対象

### Project DB
- DB ID: 343450ff-37c0-81e4-934e-f25f90284a3c
- Properties used:
  - 案件名 (title)
  - 必要スキル (multi_select)
  - 尚可スキル (multi_select)
  - 単価（万円） (number) ← budget rate
  - 仕入単価（万円） (number) ← cost rate (engineer rate ceiling reference)
  - 期間 (rich_text)
  - 勤務地 (rich_text)
  - リモート (select): フルリモート / 一部リモート / 常駐
  - 面談希望 (number)
  - 担当者 (select): 松野 / 岡本 / 共通
  - 案件詳細 (rich_text)
  - ステータス (select): 募集中 / 選考中 / 成約 / 終了 / 稼働中
  - 開始日 (date) ← use for freshness check (substitute for 受信日時)
  - last_edited_time ← primary freshness check

---

## Matching Logic

### Engineer Query (engineer_query)
1. Fetch all engineers from Engineer DB
2. Filter: イニシャル partial match (case insensitive) AND 最寄り駅 partial match
3. If 0 hits: return "一致する人員が見つかりませんでした: {initial} {station}"
4. For each matched engineer, fetch all projects from Project DB
5. Filter projects in order:
   a. ステータス == "募集中" only
   b. Freshness: last_edited_time within 4 business days (jpholiday)
   c. Skill match: all 必要スキル multi_select names exist in engineer's スキル multi_select names
   d. Gross profit check by 担当者:
      - 松野: (単価（万円） - engineer 単価（万円）) >= 5
      - 岡本: (単価（万円） - engineer 単価（万円）) >= 3
      - 共通: use 3万 threshold
6. Sort by gross profit descending
7. Generate reply text via format_project_result()

### Project Query (project_query)
1. Fetch all projects from Project DB
2. Filter: 案件名 partial match (case insensitive) AND ステータス == "募集中"
3. If 0 hits: return "一致する案件が見つかりませんでした: {name}"
4. For each matched project, fetch all engineers from Engineer DB
5. Filter engineers in order:
   a. 稼働状況 in ["稼働可能", "調整中"] (substitute for 提案対象フラグ)
   b. Freshness: last_edited_time within 21 days
   c. Skill match: all 必要スキル names exist in engineer's スキル names
   d. Gross profit check: same logic as above (use project 担当者)
6. Sort by gross profit descending
7. Generate reply text via format_engineer_result()

---

## Parallel Score (for display only - not used for filtering in this version)

| Status keyword in 備考（LINEメモ） | Score |
|---|---|
| 面談調整中 | 1.5 |
| 面談予定 | 2.0 |
| 結果待ち | 2.0 |
| オファー中 | 5.0 |
| (none) | 0 |

Calculate total from keywords found in 備考（LINEメモ）.
Display in output but do NOT filter by score (no parallel score data in DB currently).

---

## LINE Reply Format

### Engineer Query Reply (full display)
```
【{イニシャル}｜{最寄り駅}】マッチ案件 {N}件

━━━━━━━━━━━━
①{案件名}
━━━━━━━━━━━━
業務内容  : {案件詳細}
必要スキル: {必要スキル names joined by " / "}
尚可スキル: {尚可スキル names joined by " / "}
勤務地    : {勤務地}（リモート: {リモート}）
期間      : {期間}
面談      : {面談希望}回
提示単価  : {単価（万円）}万円
粗利      : {gross profit}万円
担当      : {担当者}
鮮度      : 最終更新{N}日前
━━━━━━━━━━━━
②{案件名}
...repeat same format

No match case:
【{イニシャル}｜{最寄り駅}】マッチ案件なし
（条件: 有効案件なし or スキル・粗利不一致）
```

### Project Query Reply (full display)
```
【{案件名}】マッチ人員 {N}名

━━━━━━━━━━━━
①{名前}｜{最寄り駅}
━━━━━━━━━━━━
スキル    : {スキル names joined by " / "}
稼働状況  : {稼働状況}
稼働可能日: {稼働可能日 or "未設定"}
所属      : {所属会社}
希望単価  : {単価（万円）}万円
粗利      : {gross profit}万円
並行状況  : {備考（LINEメモ）first 50 chars}
鮮度      : 最終更新{N}日前
━━━━━━━━━━━━
②{名前}｜{最寄り駅}
...repeat same format

No match case:
【{案件名}】マッチ人員なし
（条件: スキル・粗利・鮮度条件不一致）
```

---

## Function Signatures

```python
def classify_query(text: str) -> tuple[str, dict]:
    # Returns ("engineer", {"initial": "TK", "station": "渋谷"})
    # or ("project", {"name": "Java開発_〇〇社"})

def fetch_all_pages(db_id: str) -> list[dict]:
    # Fetch all pages from Notion DB with pagination

def business_days_since(dt) -> int:
    # Returns number of business days since given datetime (jpholiday)

def skill_match(required: list[str], engineer_skills: list[str]) -> bool:
    # All required skills must exist in engineer skills (partial match OK)

def calc_gross_profit(budget: float, cost: float) -> float:
    # Returns budget - cost

def engineer_query(initial: str, station: str) -> str:
    # Engineer query. Returns LINE reply string.

def project_query(name: str) -> str:
    # Project query. Returns LINE reply string.

def format_project_result(engineer: dict, projects: list) -> str:
    # Format engineer query result

def format_engineer_result(project: dict, engineers: list) -> str:
    # Format project query result

def handle_line_query(text: str) -> str | None:
    # Entry point. Returns None if text doesn't match query pattern.
```

---

## webhook_server.py Addition (3 lines only)

Add at top of handle_message():
```python
from line_query import handle_line_query
result = handle_line_query(text)
if result is not None:
    return reply_message(reply_token, result)
```

---

## .env Keys
```
NOTION_TOKEN=
ENGINEER_DB_ID=343450ff-37c0-819d-8769-fb0a8a4ceeb1
PROJECT_DB_ID=343450ff-37c0-81e4-934e-f25f90284a3c
```

---

## Error Handling
- Notion API error -> return "照会中にエラーが発生しました。しばらく後に再試行してください。"
- No match -> return appropriate no-match message
- All exceptions: try/except, log, return error message

## LINE Character Limit
- Max 5000 chars per message
- If exceeded: limit to top 5 results, append "(上位5件表示)"
