
# SPEC_affiliation_fields.md

## 目的
エンジニアDBに追加した3フィールド（所属会社/所属担当者名/所属メール）を
webhook_server.pyのregister_engineer()で保存できるようにする。

## 対象ファイル
webhook_server.py（C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py）

## 変更箇所: register_engineer()のprops構築部分

### 現状のclassify_message()が返すinfoの構造
{"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"location":"","note":""}

### 追加する処理
classify_messageのsystem promptに以下を追加して抽出項目を増やす:
- affiliation: 所属会社名（例: 「株式会社〇〇」）
- contact_name: 所属担当者名
- contact_email: 所属側のメールアドレス

### register_engineer()への追加
```python
if info.get("affiliation"):
    props["所属会社"] = {"rich_text": [{"text": {"content": info["affiliation"][:500]}}]}
if info.get("contact_name"):
    props["所属担当者名"] = {"rich_text": [{"text": {"content": info["contact_name"][:100]}}]}
if info.get("contact_email"):
    props["所属メール"] = {"email": info["contact_email"]}
```

### classify_message()のsystem promptのSingle engineer出力形式を変更
現在:
{"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"location":"","note":""}

変更後:
{"type":"engineer","name":"","skills":[],"price":0,"available_date":"","experience_years":0,"location":"","note":"","affiliation":"","contact_name":"","contact_email":""}

同様にMultiple engineers内の各engineerにも同じフィールドを追加。

## 注意
- 他の既存機能は一切変更しない
- affiliationが空文字・Noneの場合はpropsに追加しない
