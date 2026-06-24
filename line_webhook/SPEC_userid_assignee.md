# SPEC_userid_assignee.md - user_idベースの担当者判定

最終更新: 2026-05-22

## 目的
webhook_server.pyの担当者判定をsender_name（"matsuno"/"okamoto"）ではなく
LINEメッセージの送信者user_idで行うよう修正する。

## 背景
岡本は「岡本個人LINE」から「松野公式LINE」に案件/要員情報を送る。
この場合webhook_server.pyのsender_nameは常に"matsuno"になるため、
user_idで送信者を判定する必要がある。

## 岡本のuser_id
OKAMOTO_LINE_USER_ID = "Uac1d23408573586affa37577c4e2b2ab"
（config/.envにも設定済み）

## 変更対象ファイル
`ses_work/line_webhook/webhook_server.py`

## 変更内容

### register_engineer / register_project の担当者判定修正
現在の実装：
```python
assignee_name = "岡本" if sender == "okamoto" else "松野"
props["担当者"] = {"select": {"name": assignee_name}}
```

修正後：senderではなくuser_idで判定する。
両関数のシグネチャに`user_id`引数を追加して渡す方法でも可だが、
最もシンプルな方法はconfig/.envから OKAMOTO_LINE_USER_ID を取得して比較すること。

実装方針：
- モジュールレベルで `OKAMOTO_USER_ID = os.environ.get('OKAMOTO_LINE_USER_ID', '')` は既に定義済み
- register_engineer / register_projectに `user_id=""` 引数を追加
- 担当者判定を `"岡本" if user_id and user_id == OKAMOTO_USER_ID else "松野"` に変更
- 呼び出し元（process_message）からuser_idを渡す

### process_messageへのuser_id引数追加
現在: `def process_message(text, reply_token, sender, sender_token)`
修正後: `def process_message(text, reply_token, sender, sender_token, user_id="")`

handle_webhookでuser_idを取得して渡す（既にuser_idは取得済み）。

### register_engineer呼び出し箇所の修正
process_message内の全てのregister_engineer/register_project呼び出しに
`user_id=user_id`を追加。

## 注意事項
- 既存のロジックは変更しない（シグネチャ追加・引数追加のみ）
- py_compileで確認すること
- webhook_server.py以外は変更しない

## Acceptance
- [ ] register_engineerがuser_idで担当者を判定する
- [ ] register_projectが同様
- [ ] process_messageがuser_idを受け取ってregisterに渡す
- [ ] handle_webhookがuser_idをprocess_messageに渡す
- [ ] py_compile通過
