# SPEC_patch.md - mail_pipeline.py への担当者組み込みパッチ

## 目的
mail_pipeline.py に assignee.py の determine_assignee() を組み込む。
変更は最小限のパッチのみ。大規模リファクタ禁止。

## 作業ディレクトリ
C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\

## 変更内容（4箇所のみ）

### 変更1: import追加（ファイル冒頭のimport群の末尾に追加）
```python
from assignee import determine_assignee
```

### 変更2: fetch_recent_emails() の emails.append() を修正
現在:
```python
emails.append({
    "id": mail_id, "msg_id": msg_id,
    "subject": subject, "sender": sender,
    "reply_to": reply_to, "body": body,
    "attachments": attachments  # v5追加
})
```
変更後（to_addressを追加）:
```python
to_raw = decode_str(msg.get("To", "") or msg.get("Delivered-To", "") or msg.get("X-Original-To", ""))
emails.append({
    "id": mail_id, "msg_id": msg_id,
    "subject": subject, "sender": sender,
    "reply_to": reply_to, "body": body,
    "attachments": attachments,
    "to_address": to_raw
})
```

### 変更3: register_project() に assignee引数を追加
現在のシグネチャ:
```python
def register_project(info: dict, subject: str, sender: str) -> bool:
```
変更後:
```python
def register_project(info: dict, subject: str, sender: str, assignee: str = "松野") -> bool:
```
properties dictに以下を追加（既存のproperties = {...} の中）:
```python
"担当者": {"select": {"name": assignee}},
```

### 変更4: register_engineer() に assignee引数を追加
現在のシグネチャ:
```python
def register_engineer(info: dict, subject: str, sender: str) -> tuple:
```
変更後:
```python
def register_engineer(info: dict, subject: str, sender: str, assignee: str = "松野") -> tuple:
```
properties dictに以下を追加:
```python
"担当者": {"select": {"name": assignee}},
```

### 変更5: main()のループ内に担当者決定と渡しを追加
to_address取得とassignee決定をlog("処理中: ...")の直後に追加:
```python
to_address = em.get("to_address", "")
assignee = determine_assignee(to_address)
log(f"  担当者: {assignee} (宛先: {to_address[:40]})")
```
register_project呼び出しを修正:
```python
ok = register_project(info, subject, sender, assignee=assignee)
```
register_engineer呼び出しを修正:
```python
ok, notion_id = register_engineer(info, subject, sender, assignee=assignee)
```

## 確認方法
変更後に以下を実行してエラーなく起動することを確認:
```
python -c "import mail_pipeline.mail_pipeline; print('import OK')"
```

## TASKS_patch.md の完了マーク
全変更完了後にTASKS_patch.mdを全項目チェック済みに更新する。
