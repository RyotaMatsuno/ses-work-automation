# SPEC_assignee_auto.md - Notionへの担当者自動セット

最終更新: 2026-05-22

## 目的
webhook_server.pyのregister_engineer/register_project関数に
担当者カラムの自動セットを追加する。

## 変更対象ファイル
`ses_work/line_webhook/webhook_server.py`

## 変更内容

### sender → 担当者名のマッピング
- "matsuno" → "松野"
- "okamoto" → "岡本"
- その他 → "松野"（デフォルト）

### register_engineer関数（変更箇所）
propsに以下を追加：
```python
assignee_name = "岡本" if sender == "okamoto" else "松野"
props["担当者"] = {"select": {"name": assignee_name}}
```

### register_project関数（変更箇所）
同様にpropsに追加：
```python
assignee_name = "岡本" if sender == "okamoto" else "松野"
props["担当者"] = {"select": {"name": assignee_name}}
```

## 注意事項
- 既存のロジックは一切変更しない（追加のみ）
- 担当者カラムはすでにNotionのDBに存在する（セレクト型、松野/岡本/共通）
- webhook_server.py以外のファイルは変更しない
- 変更後にpy_compileで構文確認すること

## Acceptance
- [ ] register_engineerのpropsに担当者が追加される
- [ ] register_projectのpropsに担当者が追加される  
- [ ] py_compile通過
- [ ] 既存ロジック変更なし
