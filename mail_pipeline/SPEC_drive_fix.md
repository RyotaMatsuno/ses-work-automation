# SPEC.md - Drive URL PATCH修正

## 問題
mail_pipeline.py で Notion の「DriveリンクURL」フィールドへの書き込み時に
`{"rich_text": [{"text": {"content": url}}]}` という形式で書き込んでいるが、
Notionはこのフィールドをurl型として定義しているため400エラーが発生している。

エラーメッセージ: "Drive_URL is expected to be url."

## 修正内容

### 対象箇所（mail_pipeline.py）
以下のパターンを全て修正:

**修正前（rich_text型）:**
```python
properties["DriveリンクURL"] = {"rich_text": [{"text": {"content": drive_url[:2000]}}]}
```

**修正後（url型）:**
```python
properties["DriveリンクURL"] = {"url": drive_url}
```

また `add_rich_text_if_exists` でDriveリンクURLを書いている箇所も同様に
url型に変更する。

### 対象行（スキャン結果より）
- L1034-1036: PROJECT_DB向けDriveリンクURL書き込み
- L1084-1087: ENGINEER_DB向けDriveリンクURL書き込み
- L1360-1362: 追加PATCH部分のDriveリンクURL
- L1452-1455: engineer追加PATCH部分

### 追加対策: エラー時の日次コスト上限ガード
drive_url PATCHがエラーになっても処理は続行する（現状通り）。
ただし1回のメール処理でのAPI呼び出し回数を記録し、
1時間あたり500回を超えたら実行を一時停止してLINE通知する。

## 作業手順
1. バックアップ作成
2. mail_pipeline.py のDriveリンクURL書き込み箇所をurl型に修正
3. 動作確認（dry-run）
4. TASKS.md更新
