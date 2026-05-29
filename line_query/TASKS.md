# TASKS.md - line_query

Implement in this order. Mark [ ] as [x] when done.

---

## Phase 1: Foundation

- [x] 1. Load NOTION_TOKEN / ENGINEER_DB_ID / PROJECT_DB_ID from config/.env using dotenv_values
       Path: ses_work/config/.env

- [x] 2. Implement fetch_all_pages(db_id: str) -> list[dict]
       - POST /v1/databases/{db_id}/query
       - Pagination: loop while has_more=True, pass start_cursor
       - 100 results per call (page_size=100)
       - Return list of page dicts

- [x] 3. Implement business_days_since(dt) -> int
       - Accept datetime or ISO string
       - Count business days from dt to today using jpholiday
       - Saturdays, Sundays, JP holidays = non-business day

---

## Phase 2: Detection Logic

- [x] 4. Implement classify_query(text: str) -> tuple[str, dict]
       - Regex: ^([A-Za-z]{1,4})[\s/](.+)$
       - Match -> ("engineer", {"initial": ..., "station": ...})
       - No match -> ("project", {"name": text})

- [x] 5. Implement skill_match(required: list[str], engineer_skills: list[str]) -> bool
       - For each required skill, check if any engineer skill contains it (partial, case insensitive)
       - All required must match -> True
       - Empty required list -> True (no skill filter)

- [x] 6. Implement calc_gross_profit(budget: float, cost: float) -> float
       - Return budget - cost

---

## Phase 3: Query Processing

- [x] 7. Implement engineer_query(initial: str, station: str) -> str
       - Fetch all engineers
       - Filter: イニシャル partial match (case insensitive) AND 最寄り駅 partial match
       - If 0 engineers: return no-match message
       - Fetch all projects
       - Filter projects:
         a. ステータス == "募集中"
         b. business_days_since(last_edited_time) <= 4
         c. skill_match(project 必要スキル names, engineer スキル names)
         d. gross profit >= threshold (5 for 松野, 3 for 岡本/共通)
       - Sort by gross profit desc
       - Return format_project_result(engineer, matched_projects)

- [x] 8. Implement project_query(name: str) -> str
       - Fetch all projects
       - Filter: 案件名 partial match AND ステータス == "募集中"
       - If 0 projects: return no-match message
       - Use first matched project
       - Fetch all engineers
       - Filter engineers:
         a. 稼働状況 in ["稼働可能", "調整中"]
         b. business_days_since(last_edited_time) <= 21
         c. skill_match(project 必要スキル names, engineer スキル names)
         d. gross profit >= threshold by project 担当者
       - Sort by gross profit desc
       - Return format_engineer_result(project, matched_engineers)

---

## Phase 4: Formatting

- [x] 9. Implement format_project_result(engineer: dict, projects: list) -> str
       - Header: 【{イニシャル}｜{最寄り駅}】マッチ案件 {N}件
       - If empty: no-match message
       - For each project: full format per SPEC
       - If total > 5000 chars: limit to top 5, append "(上位5件表示)"

- [x] 10. Implement format_engineer_result(project: dict, engineers: list) -> str
        - Header: 【{案件名}】マッチ人員 {N}名
        - If empty: no-match message
        - For each engineer: full format per SPEC
        - If total > 5000 chars: limit to top 5, append "(上位5件表示)"

---

## Phase 5: Entry Point

- [x] 11. Implement handle_line_query(text: str) -> str | None
        - classify_query -> call engineer_query or project_query
        - Wrap all in try/except
        - On exception: log error, return "照会中にエラーが発生しました。しばらく後に再試行してください。"
        - If text doesn't match query intent: return None
          (Note: project_query catches everything non-engineer, so None is only returned
           for explicitly empty/whitespace-only text)

- [x] 12. Add __main__ test block
        - Test 1: "TK 渋谷" (engineer query)
        - Test 2: "Java開発" (project query)
        - Test 3: "AB/新宿" (slash separator engineer query)
        - Test 4: "ZZZZ 存在しない駅" (no match engineer query)
        - Print each result

---

## Phase 6: Webhook Integration

- [x] 13. Add 3 lines to webhook_server.py handle_message() top:
        ```python
        from line_query import handle_line_query
        result = handle_line_query(text)
        if result is not None:
            return reply_message(reply_token, result)
        ```
        DO NOT change any other existing logic.

---

## Completion Criteria
- [x] python line_query.py runs 4 tests without error
- [x] Output matches SPEC format
- [x] webhook_server.py addition is exactly 3 lines
