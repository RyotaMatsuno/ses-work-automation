# SPEC.md - マッチングメッセージに案件詳細・担当会社を追加

## 修正1: get_active_projects() に note と assignee を追加
### ファイル: line_webhook/webhook_server.py
### 対象行: result.append({}) の箇所（949行目付近）

現在のresult.appendに以下2フィールドを追加する:

```python
note_items = props.get("案件詳細", {}).get("rich_text", [])
note = note_items[0].get("plain_text", "")[:200] if note_items else ""

assignee_select = props.get("担当者", {}).get("select", {})
assignee = assignee_select.get("name", "") if assignee_select else ""
# 担当者がなければ input_source を試みる
if not assignee:
    src_items = props.get("input_source", {}).get("rich_text", [])
    assignee = src_items[0].get("plain_text", "")[:50] if src_items else ""
```

result.append に `"note": note, "assignee": assignee` を追加。

---

## 修正2: build_reverse_match_message_v2() に案件詳細・担当会社を表示
### ファイル: line_webhook/matching_logic.py
### 対象行: 176行目付近（case名の次の行）

OK案件・要調整案件・上振れ候補それぞれの案件名表示行の直後に以下を追加:

```python
# 担当会社
assignee = m.get("assignee", "")
if assignee:
    lines.append(f"     会社: {assignee}")
# 案件詳細（先頭60文字）
note = m.get("note", "")
if note:
    lines.append(f"     内容: {note[:60]}")
```
