# SPEC.md - get_active_projects 会社名・案件詳細フィールド修正

## 修正対象
ファイル: line_webhook/webhook_server.py
関数: get_active_projects() （919行目付近）

## 現状の問題
1. assignee を「担当者」selectから取っているが、実際は空。正しいフィールドは「所属会社名」(rich_text)
2. note を「案件詳細」から200文字で切り取っているが、原文全文が入っているので2000文字必要

## 修正内容

### assignee の取得方法を変更
変更前:
```python
assignee_select = props.get("担当者", {}).get("select", {})
assignee = assignee_select.get("name", "") if assignee_select else ""
if not assignee:
    src_items = props.get("input_source", {}).get("rich_text", [])
    assignee = src_items[0].get("plain_text", "")[:50] if src_items else ""
```

変更後:
```python
co_items = props.get("所属会社名", {}).get("rich_text", [])
assignee = co_items[0].get("plain_text", "") if co_items else ""
```

### note の文字数制限を2000文字に拡大
変更前:
```python
note = note_items[0].get("plain_text", "")[:200] if note_items else ""
```

変更後:
```python
note = note_items[0].get("plain_text", "")[:2000] if note_items else ""
```
